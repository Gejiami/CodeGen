import datetime
import json
import os
import re
import subprocess
import sys
from argparse import ArgumentParser
current_path = os.path.abspath(__file__)
root = os.path.dirname(os.path.dirname(current_path))
sys.path.append(root)

from tqdm import tqdm

from langchain_core.documents import Document

from model.connect import Openai
from model.output_parser import FileOutputParser
from model.prompt import prompt_list_for_position_and_patch, prompt_list_for_summarize_code, \
    prompt_list_for_process_instruction
from task.run_command import git_clone_repo
from utils.code_parser import get_code_parser
from model.vector_store import VectorStore
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('API_KEY')
if OPENAI_API_KEY is None:
    raise ValueError("API_KEY environment variable is not set.")

RETRY_WAIT_TIME = 30
MAX_RETRY = 5
SUFFIX = {"flutter": ".dart",
          "python": ".py"}
HOME = os.getenv('HOME')

from langchain_openai import OpenAIEmbeddings


class LLMCodeGenerator:
    def __init__(self, language, project_name, project_path, user_instruction, sha=None, model_name="gpt-4o-mini"):
        self.language = language
        self.sha = sha
        self.project_name = project_name
        self.project_path = os.path.join(project_path, project_name)
        self.user_instruction = user_instruction
        self.set_sha()
        self.non_code_files, self.code_files = self.list_files()
        self.file_codes = {}
        self.code_summary = {}
        self.embeddings_model = OpenAIEmbeddings(
            api_key=OPENAI_API_KEY
        )
        self.llm = Openai(api_key=OPENAI_API_KEY, model_name=model_name)
        self.vector_store = None

        # process user instruction
        # self.process_user_instruction()

    def set_sha(self):
        os.chdir(self.project_path)
        # check git status clean
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if result.stdout.strip():
            # directly clean
            self.restore_git_files()
            # raise RuntimeError(
            #     "Uncommitted changes detected. Please commit or stash your changes before switching commits.")
        if self.sha:
            subprocess.run(["git", "checkout", self.sha], check=True)
        else:
            self.sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()

    def get_changed_filenames(self, commit1, commit2):
        os.chdir(self.project_path)
        result = subprocess.run(["git", "diff", commit1, commit2], check=True, capture_output=True,
                                text=True, errors='ignore')
        diff = result.stdout
        lines = diff.splitlines()
        old_files, new_files = set(), set()
        for idx, line in enumerate(lines):
            if line.startswith("diff --git"):
                parts = line.split()  # Split the line and get the file path
                if len(parts) >= 3:
                    # remove "a/", "b/"
                    old_file = os.path.join(self.project_path, parts[2][2:])
                    new_file = os.path.join(self.project_path, parts[3][2:])
                    info1, info2 = lines[idx+1], lines[idx+2]
                    old_valid, new_valid = False, False
                    if info1.startswith('deleted'):  # delete
                        old_valid = True
                    elif info1.startswith('new file'):  # add
                        new_valid = True
                    elif info1.startswith('index'):  # edit
                        old_valid, new_valid = True, True
                    elif info1.startswith('similarity'):
                        if info2.startswith('rename'):
                            old_valid, new_valid = True, True
                        elif info2.startswith('copy'):
                            new_valid = True
                    elif info1.startswith('old mode'):  # mode change
                        pass
                    if old_valid and old_file.endswith(SUFFIX[self.language]):
                        old_files.add(old_file)
                    if new_valid and new_file.endswith(SUFFIX[self.language]):
                        new_files.add(new_file)
        return list(old_files), list(new_files)

    def list_files(self):
        non_code_files = []
        code_files = []

        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                file_path = os.path.join(root, file)
                if file_path.endswith(SUFFIX[self.language]):
                    code_files.append(file_path)
                else:
                    non_code_files.append(file_path)
        return non_code_files, code_files

    def read_file(self, file_name):
        with open(file_name, 'r', encoding='utf-8') as file:
            content = file.read()
        return content

    def read_file_with_index(self, file_name):
        with open(file_name, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        numbered_lines = []
        # start=0 or 1?
        for idx, line in enumerate(lines, start=0):
            numbered_line = f"[{idx}]{line}"
            numbered_lines.append(numbered_line)
            # print(numbered_line)
        return ''.join(numbered_lines)

    def parse_file(self, file_name, if_code=False):
        if if_code:
            code_parser = get_code_parser(self.language)
            return code_parser.sort_code(file_name)
        else:
            return self.read_file(file_name)

    def write_code(self, output_project_path, code):
        with open(output_project_path, 'w', encoding='utf-8') as file:
            file.write(code)

    def modify_code(self, file_path, position, original, patched):
        message = ''
        if file_path not in self.code_files:
            message += f'No file: {file_path} found in project directory. Please check the file name again carefully. '
            return False, message
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        line_len = []
        current_len = 0
        for line in lines:
            current_len += len(line)
            line_len.append(current_len)
        # case when modified patch is empty
        if not patched or patched == '...':
            message += "Patch code is empty. "
            return False, message
        # case when original position is empty
        if not original or original == '...':
            message += "Original code is empty. "
        # get position case when invalid int
        try:
            start = int(position.split(',')[0])
            end = int(position.split(',')[1])
        except:
            message += "Patch position is empty. Please include position in your output. "
            # return False, message
            start = 0
            end = len(lines)
            # at least one of original or position should exist
            if not original or original == '...':
                return False, message
        if not original or original == '...':
            modified_code = ''.join(lines[:start]) + patched + ''.join(lines[start:])
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(modified_code)
            message += file_path + " file modified successfully. "
            return True, message
        else:
            # search file start from position to whole
            match = None
            while not match:
                start = max(0, start - 5)
                end = min(len(lines), end + 5)
                # \s* represents any number of space, indent or \n
                content = ''.join(lines[start:end])
                pattern = re.compile(r'\s*'.join(re.escape(line.strip()) for line in original.strip().splitlines()),
                                     re.MULTILINE)
                # search
                match = pattern.search(content)
                # stop
                if start == 0 and end == len(lines):
                    break
            if match:
                message += f"Match code found at ({start},{end}) in file {file_path}. "
                original_match = match.group()
                modified_code = ''.join(lines[:start]) + ''.join(lines[start:end]).replace(original_match, patched) \
                                + ''.join(lines[end:])
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(modified_code)
                message += file_path + " file modified successfully. "
                return True, message
            else:
                message += f"No match code snippets: <original>{original}</code> found in {file} file_path. "
                return False, message

    # def get_user_instruction(self, instruction):
    #     self.user_instruction = instruction
    #     print('User instruction:', self.user_instruction)

    def process_user_instruction(self):
        prompt_list = prompt_list_for_process_instruction()
        input_dict = {"statement": self.user_instruction}
        response = self.llm.invoke(prompt_list, input_dict, None, False)
        self.user_instruction = f"<statement>{self.user_instruction}</statement>\n<guide>{response.content}</guide>"
        
    def update_documents_to_vector_store(self, update_files, if_code=True):
        for file_name in tqdm(update_files):
            snippets = self.parse_file(file_name, if_code=if_code)
            # print(idx, file_name)
            docs = []
            for snippet in snippets:
                class_name, content, position = snippet[0], snippet[1], snippet[2]
                metadata = {'file_name': file_name,
                            'if_code': if_code,
                            'class_name': class_name, }
                docs.append(Document(page_content=content, metadata=metadata))
            if docs:
                self.vector_store.add_documents(docs)

    def update_summary_documents_to_vector_store(self, update_files, if_code=True):
        # parse dart code and get summary from llm
        for file_name in tqdm(update_files):
            prompt_list = prompt_list_for_summarize_code(self.language, True)
            snippets = self.parse_file(file_name, if_code=if_code)
            # print(idx, file_name)
            docs = []
            for snippet in snippets:
                class_name, content, position = snippet[0], snippet[1], snippet[2]
                input_dict = {"file_name": file_name, "source_code": content}
                try:
                    response = self.llm.invoke(prompt_list=prompt_list, input_dict=input_dict, output_parser=None, record=False)
                    summary = response.content
                    metadata = {'file_name': file_name,
                                'if_code': if_code,
                                'class_name': class_name, }
                    docs.append(Document(page_content=summary, metadata=metadata))
                except Exception as e:
                    print("Error occurred when creating code summary:", e)
                    continue
            if docs:
                self.vector_store.add_documents(docs)

    def set_vector_store(self, refresh=False, update_from_sha=None):
        self.vector_store = VectorStore(self.embeddings_model, self.project_name, self.sha, update_from_sha)

        # If local vector store data exists
        if not refresh:
            db_exists = self.vector_store.load_db()
            if db_exists == 1:
                return
            elif db_exists == 2:
                old_files, new_files = self.get_changed_filenames(update_from_sha, self.sha)
                self.vector_store.remove_documents(old_files)
                update_files = new_files
            else:
                update_files = self.code_files
        else:
            self.vector_store.load_refreshed_db()
            update_files = self.code_files

        # embedding with original code
        # self.update_documents_to_vector_store(update_files)

        # embedding with summarized code
        self.update_summary_documents_to_vector_store(update_files)

        # save db
        self.vector_store.save_db()

    def create_git_diff(self):
        result = subprocess.run(
            ["git", "diff", "--ignore-space-change"],
            check=True,
            capture_output=True,
            text=True
        )
        diff_output = result.stdout
        return diff_output

    def validate_modification(self, modifications):
        # clean git status
        self.restore_git_files()
        all_success, all_message = True, ''
        for idx, mod in enumerate(modifications, start=1):
            success, message = self.modify_code(mod[0], mod[1], mod[2], mod[3])
            # validate compilation
            if success:
                file_path = mod[0]
                if self.language == 'flutter':
                    try:
                        input_data = "y\ny\ny\ny\n"
                        process = subprocess.Popen("fvm dart analyze", shell=True, stdin=subprocess.PIPE,
                                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        stdout, stderr = process.communicate(input=input_data, timeout=120)
                        message += f"Syntax check passed for {file_path}."
                    except subprocess.CalledProcessError as e:
                        message += f"Syntax check failed for {file_path}.\n" + e.stderr
                elif self.language == 'python':
                    try:
                        result = subprocess.run(
                            ['python', '-m', 'py_compile', file_path],
                            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        message += f"Syntax check passed for {file_path}."
                    except subprocess.CalledProcessError as e:
                        message += f"Syntax check failed for {file_path}.\n" + e.stderr
            all_success = all_success and success
            all_message += '# modification ' + str(idx) + '\n' + message
        if all_success:
            print("Patch validation passed.")
        else:
            print("Patch validation failed. Error message:", all_message)
        return all_success, all_message

    def generate_patch(self):
        log_message = ''
        matched_docs = self.vector_store.match_documents(self.user_instruction)
        matched_files = list(set([doc.metadata['file_name'] for doc in matched_docs]))
        print("matched_files:\n", ', '.join(matched_files))
        code_with_location = ''
        for index, matched_file in enumerate(matched_files):
            prefix = f'[start of {matched_file}]'
            postfix = f'[end of {matched_file}]\n'
            code = self.read_file(matched_file)
            code_with_location += prefix + code + postfix
        input_dict = {"code_with_location": code_with_location, "user_instruction": self.user_instruction}
        prompt_list = prompt_list_for_position_and_patch(language=self.language)
        modifications = self.llm.invoke(prompt_list=prompt_list, input_dict=input_dict, output_parser=FileOutputParser())

        if not modifications:
            all_success = False
            all_message = "Can not parse modification patch in output. Please make sure you output in the correct format."
        else:
            all_success, all_message = self.validate_modification(modifications)
        log_message += all_message
        # iteration
        iteration_number = 1
        while not all_success and iteration_number <= 3:
            print(f"Iteration {iteration_number}:")
            modifications = self.llm.iterate(all_message, iteration_number, output_parser=FileOutputParser())
            if not modifications:
                iteration_number += 1
                continue
            all_success, all_message = self.validate_modification(modifications)
            iteration_number += 1
            log_message += all_message
        return matched_docs, all_success, log_message

    def restore_git_files(self):
        os.chdir(self.project_path)
        subprocess.run(["git", "restore", "--staged", "."], check=True)
        subprocess.run(["git", "restore", "."], check=True)
        subprocess.run(["git", "clean", "-fd"], check=True)



def main(home_path, repo, repo_type, language, commit_sha, last_commit_sha, model_name, user_instruction, log_dir):
    start_time = datetime.datetime.now()
    if repo_type == "github":
        git_clone_repo(repo, False)
        project_name = repo.split('/')[1]
    else:
        project_name = repo
    generator = LLMCodeGenerator(language=language, project_name=project_name,
                                                 project_path=home_path,
                                                 user_instruction=user_instruction, sha=commit_sha,
                                             model_name=model_name)

    generator.set_vector_store(refresh=False, update_from_sha=last_commit_sha)
    log_info = dict()
    matched_docs, all_success, all_message = generator.generate_patch()
    print('Log message:\n', all_message)
    model_patch = generator.create_git_diff()
    print('Update patch applied:\n', model_patch)
    token_usage = generator.llm.token_usage
    end_time = datetime.datetime.now()
    log_info["repo"] = repo
    log_info["repo_type"] = repo_type
    log_info["language"] = language
    log_info["commit_sha"] = commit_sha
    log_info["token_usage"] = token_usage
    log_info["model_patch"] = model_patch
    log_info["model_name"] = model_name
    log_info["run_time"] = (end_time - start_time).total_seconds()
    log_info["matched_docs"] = str(matched_docs)
    log_info["log_message"] = all_message
    log_info["success"] = all_success

    #save log
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    with open(os.path.join(log_dir, f'{project_name}_{commit_sha}_log.json'), 'a', encoding='utf-8') as f:
        json.dump(log_info, f)
    print('Log saved to',os.path.join(log_dir, f'{project_name}_{commit_sha}_log.json'), datetime.datetime.now())

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--repo", type=str, help="Full name of the repository")
    parser.add_argument("--repo_type", type=str, choices=["local", "github"],
                        help="Whether it's a local or github repo")
    parser.add_argument("--language", type=str, choices=["flutter", "python"],
                        help="What language/framework is the repo based on")
    parser.add_argument("--user_instruction", type=str, help="User's change request.")
    parser.add_argument("--commit_sha", type=str, default=None,
                        help="The sha of the commit to modify. Use lastest commit as default")
    parser.add_argument("--last_commit_sha", type=str, default=None,
                        help="The sha of last commit. Use the second lastest commit as default")
    parser.add_argument("--model_name", type=str, default="gpt-4o", help="Model name of Openai LLM API.")
    parser.add_argument("--home_path", type=str, default=HOME, help="Path to the repo. Use home directory as default.")
    parser.add_argument("--log_dir", type=str, default=os.path.join(root,'log'), help="Full path to the log dir.")
    args = parser.parse_args()
    main(**vars(args))

