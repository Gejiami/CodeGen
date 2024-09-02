import ast
import re
import astor


class CodeParser:
    def sort_code(self, file_path):
        pass


class DartParser(CodeParser):
    def parse_comments(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # search for single and multiple lines comments
        comment_pattern = re.compile(
            r'//.*?$|/\*.*?\*/', re.DOTALL | re.MULTILINE
        )

        matches = comment_pattern.finditer(content)

        comments_with_positions = []
        for match in matches:
            comment = match.group(0)
            start = match.start()
            end = match.end()
            comments_with_positions.append((comment, (start, end)))

        return comments_with_positions

    def parse_classes(self, file_path):
        # comments
        comments_with_positions = self.parse_comments(file_path)

        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # search for abstract class, class and mixin
        class_pattern = re.compile(
            r'\b(abstract\s+class|class|mixin)\s+([_\w]+)\s*(?:extends\s+[_\w<>]+\s*)?(?:implements\s+[_\w<>,\s]+\s*)?'
            r'(?:with\s+[_\w<>,\s]+\s*)?\s*{',
            re.MULTILINE
        )

        matches = class_pattern.finditer(content)

        classes_with_code = []
        class_ranges = []
        for match in matches:
            class_keyword, class_name = match.group(1), match.group(2)
            start = match.start()
            brace_count = 0
            end = start

            for i in range(start, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break

            # check if class is inside comment
            flag = True
            for comment, position in comments_with_positions:
                if position[0] <= start and position[1] >= end:
                    flag = False
                    break
            if flag:
                class_code = content[start:end].strip()
                classes_with_code.append((class_name, class_code, (start, end)))
                class_ranges.append((start, end))

        # extract non class code
        non_class_with_code = []
        last_end = 0
        for start, end in class_ranges:
            if last_end < start:
                non_class_code = content[last_end:start].strip()
                if non_class_code:
                    non_class_with_code.append(('', non_class_code, (last_end, start)))
            last_end = end
        if last_end < len(content):
            non_class_code = content[last_end:].strip()
            if non_class_code:
                non_class_with_code.append(('', non_class_code, (last_end, len(content))))

        return classes_with_code, non_class_with_code

    def sort_code(self, file_path):
        classes_with_code, non_class_with_code = self.parse_classes(file_path)
        code = classes_with_code + non_class_with_code
        code.sort(key=lambda x: x[-1][0])
        return code


class PythonParser(CodeParser):
    def parse_classes(self, file_path):
        with open(file_path, 'r') as file:
            content = file.readlines()
            code = ''.join(content)
            tree = ast.parse(code, filename=file_path)

        classes_with_code = []
        class_ranges = []

        class CodeSegmentVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_class = None
                self.code = code

            def visit_ClassDef(self, node: ast.ClassDef):
                self.current_class = node.name
                self._process_node(node)
                self.generic_visit(node)

            def visit_FunctionDef(self, node: ast.FunctionDef):
                self._process_node(node)
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self._process_node(node)
                self.generic_visit(node)

            def _process_node(self, node: ast.AST):
                if hasattr(node, 'lineno'):
                    start_lineno = node.lineno
                    end_lineno = getattr(node, 'end_lineno', start_lineno)
                    segment_code = astor.to_source(node).strip()
                    classes_with_code.append(('' if not self.current_class else self.current_class, segment_code,
                                              (start_lineno, end_lineno)))
                    class_ranges.append((start_lineno, end_lineno))

            def _get_code_lines(self, start_lineno, end_lineno):
                lines = self.code.splitlines(True)
                if start_lineno > len(lines):
                    return ''
                return ''.join(lines[start_lineno - 1:end_lineno])

        visitor = CodeSegmentVisitor()
        visitor.visit(tree)

        non_class_with_code = []
        last_end = 0
        for start, end in class_ranges:
            if last_end < start:
                non_class_code = ''.join(content[last_end:start])
                if non_class_code:
                    non_class_with_code.append(('', non_class_code, (last_end, start)))
            last_end = end
        if last_end < len(content):
            non_class_code = ''.join(content[last_end:])
            if non_class_code:
                non_class_with_code.append(('', non_class_code, (last_end, len(content))))

        return classes_with_code, non_class_with_code

    def sort_code(self, file_name):
        classes_with_code, non_class_with_code = self.parse_classes(file_name)
        code = classes_with_code + non_class_with_code
        code.sort(key=lambda x: x[-1][0])
        return code


def get_code_parser(language):
    if language.lower() == "python":
        return PythonParser()
    elif language.lower() == "flutter":
        return DartParser()
    else:
        raise ValueError(f"Unsupported language {language}.")
