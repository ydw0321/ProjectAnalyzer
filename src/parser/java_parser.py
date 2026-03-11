from tree_sitter import Language, Parser
from tree_sitter_java import language as java_language


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
        """提取类、方法、以及方法调用关系"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source_code = f.read()

        tree = self.parser.parse(bytes(source_code, 'utf8'))
        root_node = tree.root_node

        classes = []
        methods = []
        calls = []

        class_info = {'name': '', 'start': 0, 'end': 0}

        def find_class_declarations(node):
            nonlocal class_info
            if node.type == 'class_declaration':
                name_node = node.child_by_field_name('name')
                class_name = name_node.text.decode('utf-8') if name_node else ''
                classes.append(class_name)

                old_class = class_info
                class_info = {'name': class_name, 'start': node.start_byte, 'end': node.end_byte}

                for child in node.children:
                    find_class_declarations(child)

                class_info = old_class
            else:
                for child in node.children:
                    find_class_declarations(child)

        def find_method_declarations(node):
            nonlocal class_info
            if node.type == 'method_declaration':
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

            for child in node.children:
                find_method_declarations(child)

        def find_method_invocations(node):
            if node.type == 'method_invocation':
                name_node = node.child_by_field_name('name')
                if name_node:
                    callee = name_node.text.decode('utf-8')
                    calls.append({
                        'callee': callee,
                        'start_byte': node.start_byte,
                        'end_byte': node.end_byte
                    })

            for child in node.children:
                find_method_invocations(child)

        # 合并遍历：先找类，再在同一遍历中找方法
        def find_class_and_methods(node):
            nonlocal class_info
            if node.type == 'class_declaration':
                name_node = node.child_by_field_name('name')
                class_name = name_node.text.decode('utf-8') if name_node else ''
                classes.append(class_name)
                
                old_class = class_info
                class_info = {'name': class_name, 'start': node.start_byte, 'end': node.end_byte}
                
                # 在类内部查找方法
                for child in node.children:
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
                    find_method_invocations(child)
            else:
                for child in node.children:
                    find_class_and_methods(child)

        find_class_and_methods(root_node)

        all_method_names = {m['name'] for m in methods}
        filtered_calls = []
        for call in calls:
            if call['callee'] in all_method_names:
                for m in methods:
                    if m['start_byte'] <= call['start_byte'] <= m['end_byte']:
                        filtered_calls.append({
                            'caller': m['name'],
                            'callee': call['callee']
                        })
                        break

        return classes, methods, filtered_calls
