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
