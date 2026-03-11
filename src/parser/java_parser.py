from tree_sitter import Language, Parser
from tree_sitter_java import language as java_language
import re


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
        
        # 解析成员变量（字段）- 使用正则表达式
        fields = self._extract_fields_regex(source_code)
        
        # 建立字段映射
        field_map = {f['name']: f['type'] for f in fields}
        
        classes = []
        methods = []
        calls = []  # 同文件内调用

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
                
                methods.append({
                    'name': method_name,
                    'class_name': class_info['name'],
                    'code': method_code,
                    'start_byte': start_byte,
                    'end_byte': end_byte
                })
                
                # 继续在方法内查找调用
                for child in node.children:
                    find_method_calls(child, class_info['name'], method_name, field_map)
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
                        receiver_text = source_code[receiver.start_byte:receiver.end_byte]
                        # 检查是否是成员变量调用（不是 this、super 或局部变量）
                        if not receiver_text.startswith('this') and not receiver_text.startswith('super'):
                            target_field = receiver_text
                            # 尝试通过字段类型推断目标类
                            target_class = fmap.get(target_field)  # 直接使用 get
                    
                    # 确定调用类型和目标类
                    if target_field:
                        # 跨类调用
                        calls.append({
                            'caller': current_method,
                            'caller_class': current_class,
                            'callee': method_name,
                            'callee_class': target_class or 'Unknown',
                            'target_field': target_field,
                            'type': 'external'
                        })
                    else:
                        # 同类调用
                        calls.append({
                            'caller': current_method,
                            'caller_class': current_class,
                            'callee': method_name,
                            'callee_class': current_class,
                            'target_field': None,
                            'type': 'internal'
                        })

            for child in node.children:
                find_method_calls(child, current_class, current_method, fmap)

        find_class_and_methods(root_node)

        # 分离内部调用和外部调用
        all_method_names = {m['name'] for m in methods}
        internal_calls = []
        external_calls = []
        
        for call in calls:
            # 如果是被调用方在本文件中声明的方法，则是内部调用
            if call['callee'] in all_method_names and call['type'] == 'internal':
                # 找到对应的方法获取其类
                for m in methods:
                    if m['name'] == call['callee'] and m['start_byte'] <= call.get('start_byte', 0) <= m['end_byte']:
                        internal_calls.append({
                            'caller': call['caller'],
                            'caller_class': call['caller_class'],
                            'callee': call['callee'],
                            'callee_class': m['class_name'],
                            'type': 'internal'
                        })
                        break
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
        except:
            pass
        return None
