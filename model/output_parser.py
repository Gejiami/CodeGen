import re

from langchain_core.output_parsers import StrOutputParser

class DartOutputParser(StrOutputParser):
    def parse(self, text):
        if text.startswith("```dart\n") and text.endswith("```"):
            text = text[8:-3]
        return text.strip()


class PatchOutputParser(StrOutputParser):
    def parse(self, text):
        if text.startswith("```patch\n") and text.endswith("```"):
            text = text[9:-3]
        return text.strip()

class FileOutputParser(StrOutputParser):
    def parse(self, text):
        if text.startswith("```\n") and text.endswith("```"):
            text = text[4:-3]
        # regex
        pattern = re.compile(
            r'# modification \d+\n<file>(.*?)</file>\n<position>(.*?)</position>\n'
            r'<original>(.*?)</original>\n<patched>(.*?)</patched>',
            re.DOTALL)

        match = pattern.search(text)
        modified_patches = []
        if match:
            file_name = match.group(1).strip()
            position = match.group(2).strip()
            original = match.group(3).strip()
            patched = match.group(4).strip()

            # print("File:", file_name)
            # print("Position:", position)
            # print("Original:", original)
            # print("Patched:", patched)
            modified_patches.append((file_name, position, original, patched))
        else:
            print("No match found")
        return modified_patches