from tree_sitter import Language, Parser
from tree_sitter_java import language as java_language
import re
import logging


logger = logging.getLogger(__name__)


class JavaParser:
    def __init__(self):
        self.parser = Parser(Language(java_language()))

    def extract_methods(self, file_path):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source_code = f.read()

        tree = self.parser.parse(bytes(source_code, 'utf8'))
        root_node = tree.root_node

        methods = []

        def find_method_declarations(node):
            if node.type == 'method_declaration':
                name_node = node.child_by_field_name('name')
                method_name = name_node.text.decode('utf-8') if name_node else ''

                start_byte = node.start_byte
                end_byte = node.end_byte
                method_code = source_code[start_byte:end_byte]

                methods.append({
                    'name': method_name,
                    'code': method_code
                })

            for child in node.children:
                find_method_declarations(child)

        find_method_declarations(root_node)

        return methods

    def extract_with_calls(self, file_path):
        """提取类、方法、以及方法调用关系（支持跨类调用）"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source_code = f.read()

        tree = self.parser.parse(bytes(source_code, 'utf8'))
        root_node = tree.root_node

        # 解析 import 语句
        imports = self._extract_imports(source_code)
        imported_simple_names = {
            imp.split('.')[-1]: imp
            for imp in imports
            if imp and not imp.endswith('.*')
        }
        
        # 解析成员变量（字段）- 使用正则表达式
        fields = self._extract_fields_regex(source_code)
        
        # 建立字段映射
        field_map = {f['name']: f['type'] for f in fields}
        
        classes = []
        methods = []
        calls = []  # 同文件内调用
        methods_by_class = {}

        class_info = {'name': '', 'start': 0, 'end': 0}

        def find_class_and_methods(node):
            nonlocal class_info
            if node.type == 'class_declaration':
                name_node = node.child_by_field_name('name')
                class_name = name_node.text.decode('utf-8') if name_node else ''
                classes.append(class_name)
                
                old_class = class_info
                class_info = {'name': class_name, 'start': node.start_byte, 'end': node.end_byte}
                
                # 在类内部查找字段声明
                for child in node.children:
                    if child.type == 'field_declaration':
                        field_info = self._extract_field(child, source_code)
                        if field_info:
                            fields.append(field_info)
                            field_map[field_info['name']] = field_info['type']
                    
                    # 在类内部查找方法
                    find_class_and_methods(child)
                
                class_info = old_class
            elif node.type == 'method_declaration':
                name_node = node.child_by_field_name('name')
                method_name = name_node.text.decode('utf-8') if name_node else ''
                
                start_byte = node.start_byte
                end_byte = node.end_byte
                method_code = source_code[start_byte:end_byte]
                
                param_count = self._count_method_params(node)

                methods.append({
                    'name': method_name,
                    'class_name': class_info['name'],
                    'param_count': param_count,
                    'code': method_code,
                    'start_byte': start_byte,
                    'end_byte': end_byte
                })
                methods_by_class.setdefault(class_info['name'], {}).setdefault(method_name, set()).add(param_count)

                local_vars = self._extract_local_vars_regex(method_code)
                param_vars = self._extract_method_params(node, source_code)
                method_field_map = dict(field_map)
                method_field_map.update(local_vars)
                method_field_map.update(param_vars)
                
                # 继续在方法内查找调用
                for child in node.children:
                    find_method_calls(child, class_info['name'], method_name, method_field_map)
            else:
                for child in node.children:
                    find_class_and_methods(child)

        def find_method_calls(node, current_class, current_method, fmap):
            """递归查找方法调用"""
            if node.type == 'method_invocation':
                name_node = node.child_by_field_name('name')
                if name_node:
                    method_name = name_node.text.decode('utf-8')
                    
                    # 检查是否是 field.method() 形式
                    target_class = None
                    target_field = None
                    
                    # 获取 receiver 对象
                    receiver = node.child_by_field_name('object')
                    if receiver:
                        # source_code 已经是字符串
                        receiver_text = source_code[receiver.start_byte:receiver.end_byte].strip()
                        receiver_root = receiver_text.split('.', 1)[0]

                        # this.xxx.method() 场景：提取 this 后的字段名
                        if receiver_text.startswith('this.'):
                            receiver_root = receiver_text[len('this.'):].split('.', 1)[0]

                        # super.xxx() 视为同类/父类调用，不标记 external
                        if not receiver_text.startswith('super'):
                            target_field = receiver_root
                            # 尝试通过字段/参数/局部变量类型推断目标类
                            target_class = fmap.get(target_field)

                            # 静态调用场景: ClassName.method()
                            if not target_class and receiver_root and receiver_root[0].isupper():
                                target_class = receiver_root

                            # import 辅助消歧：优先使用明确导入的类
                            if not target_class and receiver_root in imported_simple_names:
                                target_class = receiver_root

                    arg_count = self._count_call_args(node)
                    
                    # 确定调用类型和目标类
                    if target_field:
                        # 跨类调用
                        calls.append({
                            'caller': current_method,
                            'caller_class': current_class,
                            'callee': method_name,
                            'callee_class': target_class or 'Unknown',
                            'arg_count': arg_count,
                            'target_field': target_field,
                            'type': 'external',
                            'call_start_byte': node.start_byte,
                            'call_end_byte': node.end_byte
                        })
                    else:
                        # 同类调用
                        calls.append({
                            'caller': current_method,
                            'caller_class': current_class,
                            'callee': method_name,
                            'callee_class': current_class,
                            'arg_count': arg_count,
                            'target_field': None,
                            'type': 'internal',
                            'call_start_byte': node.start_byte,
                            'call_end_byte': node.end_byte
                        })

            for child in node.children:
                find_method_calls(child, current_class, current_method, fmap)

        find_class_and_methods(root_node)

        # 分离内部调用和外部调用
        internal_calls = []
        external_calls = []
        
        for call in calls:
            # 同类调用：仅当被调用方法在当前类中存在时才记为 internal
            if call['type'] == 'internal':
                caller_class = call.get('caller_class', '')
                class_methods = methods_by_class.get(caller_class, {})
                expected_param_counts = class_methods.get(call['callee'], set())
                arg_count = call.get('arg_count', -1)
                if expected_param_counts and (arg_count in expected_param_counts or len(expected_param_counts) == 1):
                    internal_calls.append({
                        'caller': call['caller'],
                        'caller_class': caller_class,
                        'callee': call['callee'],
                        'callee_class': caller_class,
                        'arg_count': arg_count,
                        'type': 'internal'
                    })
            elif call['type'] == 'external':
                external_calls.append(call)

        return {
            'classes': classes,
            'methods': methods,
            'fields': fields,
            'imports': imports,
            'internal_calls': internal_calls,
            'external_calls': external_calls,
            'all_calls': calls
        }
    
    def _extract_imports(self, source_code):
        """提取 import 语句"""
        imports = []
        import_pattern = r'import\s+([\w\.]+)\s*;'
        for match in re.finditer(import_pattern, source_code):
            imports.append(match.group(1))
        return imports
    
    def _extract_fields_regex(self, source_code):
        """使用正则表达式提取字段声明"""
        fields = []
        # 匹配 private/public/protected 字段声明
        pattern = r'(?:private|public|protected)\s+([\w<>]+(?:<[\w\s,]+>)?)\s+(\w+)\s*[;=]'
        for match in re.finditer(pattern, source_code):
            type_name = match.group(1)
            field_name = match.group(2)
            # 简化类型名
            if '.' in type_name:
                type_name = type_name.split('.')[-1]
            # 移除泛型
            if '<' in type_name:
                type_name = type_name.split('<')[0]
            fields.append({
                'name': field_name,
                'type': type_name,
                'start_byte': match.start(),
                'end_byte': match.end()
            })
        return fields
    
    def _extract_field(self, node, source_code):
        """提取字段声明"""
        try:
            type_text = ''
            name_text = ''
            
            for child in node.children:
                # 获取类型
                if child.type in ['type', 'unann_type']:
                    type_text = source_code[child.start_byte:child.end_byte]
                # 获取变量名
                elif child.type == 'variable_declarator':
                    for c in child.children:
                        if c.type == 'identifier':
                            name_text = source_code[c.start_byte:c.end_byte]
                            break
            
            if name_text:
                # 简化类型名
                if '.' in type_text:
                    type_name = type_text.split('.')[-1]
                else:
                    type_name = type_text.split()[-1] if type_text else 'Object'
                
                return {
                    'name': name_text,
                    'type': type_name,
                    'start_byte': node.start_byte,
                    'end_byte': node.end_byte
                }
        except Exception as e:
            logger.debug("字段提取失败: start=%s, end=%s, error=%s", node.start_byte, node.end_byte, e)
        return None

    def _extract_method_params(self, method_node, source_code):
        """提取方法参数类型映射（用于 receiver 类型推断）"""
        param_map = {}
        params_node = method_node.child_by_field_name('parameters')
        if not params_node:
            return param_map

        for child in params_node.children:
            if child.type not in {'formal_parameter', 'spread_parameter'}:
                continue

            type_node = child.child_by_field_name('type')
            name_node = child.child_by_field_name('name')
            if not type_node or not name_node:
                continue

            type_name = source_code[type_node.start_byte:type_node.end_byte]
            param_name = source_code[name_node.start_byte:name_node.end_byte]
            param_map[param_name] = self._normalize_type_name(type_name)

        return param_map

    def _count_method_params(self, method_node):
        params_node = method_node.child_by_field_name('parameters')
        if not params_node:
            return 0
        count = 0
        for child in params_node.children:
            if child.type in {'formal_parameter', 'spread_parameter'}:
                count += 1
        return count

    def _count_call_args(self, call_node):
        args_node = call_node.child_by_field_name('arguments')
        if not args_node:
            return 0
        named_children = [c for c in args_node.children if getattr(c, 'is_named', False)]
        return len(named_children)

    def _normalize_type_name(self, type_name):
        if '.' in type_name:
            type_name = type_name.split('.')[-1]
        if '<' in type_name:
            type_name = type_name.split('<')[0]
        return type_name.strip() or 'Object'

    def _extract_local_vars_regex(self, method_code):
        """提取方法体内局部变量声明（用于调用目标类推断）"""
        local_vars = {}
        pattern = r'([A-Z][\w\.]*(?:<[^>]+>)?)\s+(\w+)\s*(?:=|;|,)'

        for match in re.finditer(pattern, method_code):
            type_name = self._normalize_type_name(match.group(1))
            var_name = match.group(2)

            local_vars[var_name] = type_name

        return local_vars
