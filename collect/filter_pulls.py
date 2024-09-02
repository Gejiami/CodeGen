import json
import os
import re
from dotenv import load_dotenv
import requests
from unidiff import PatchSet

load_dotenv()
# GitHub API configuration token
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')


# header
headers = {
    'Authorization': f'token {GITHUB_TOKEN}'
}

# file path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATCHES_PATH = 'git_datasets/filter_patches'
INSTANCE_PATH = 'git_datasets/task_instances'

def find_test_dir(repo_owner, repo_name):
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"

    # get default branch
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    repo_data = response.json()
    default_branch = repo_data.get('default_branch')
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/git/trees/{default_branch}?recursive=1"

    # get repo tree
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    repo_tree = response.json()

    directories = set()
    files = set()
    for item in repo_tree.get('tree', []):
        path = item['path']
        if item['type'] == 'tree':
            directories.add(path)
        elif item['type'] == 'blob':
            files.add(path)

    # locate test folder
    for file_path in files:
        if file_path.endswith('pubspec.lock'):
            directory = os.path.dirname(file_path)
            test_folder_path = os.path.join(directory, 'test')

            if test_folder_path in directories:
                print(f"Found test folder at: {test_folder_path} for repository", os.path.join(repo_owner,repo_name))
                return test_folder_path

    # No test folder found
    print("No test folder found in the repository", os.path.join(repo_owner,repo_name))
    return None


def get_files_in_directory(repo_owner, repo_name, directory):
    """ get all files in the directory"""
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{directory}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # make sure request success
    return response.json()

def get_last_commit_message(repo_owner, repo_name, file_path):
    """ get the latest commit of the file"""
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/commits?path={file_path}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    commits = response.json()
    if commits:
        message = commits[0]['commit']['message']
        return message
    return 'No commits found'

def filter_pull_numbers(repo_owner, repo_name, directory):
    """ traverse directory and filter pull number"""
    pull_numbers = set()
    try:
        items = get_files_in_directory(repo_owner, repo_name, directory)
        # stack
        while items:
            item = items.pop()
            if item['type'] == 'file':  # process file
                file_path = item['path']
                last_commit_message = get_last_commit_message(repo_owner, repo_name, file_path)
                message = last_commit_message.split('\n')[0]
                pattern = r'\(#(\d+)\)'
                match = re.search(pattern, message)
                if match:
                    pull_numbers.add(match.group(1))
                print(f'File: {file_path}, Last commit message: {message}')
            elif item['type'] == 'dir':  # process sub dir
                items = items + get_files_in_directory(repo_owner, repo_name, item['path'])
    except requests.RequestException as e:
        print(f'Error processing directory {directory}: {e}')
    return list(pull_numbers)

def get_pull_request(repo_owner, repo_name, pull_number):
    """extract data from given pull request"""
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pull_number}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_pull_commit_detail(pull):
    text = pull["title"] if pull["title"] else ""
    text += "\n" + (pull["body"] if pull["body"] else "")

    # get pull comments
    comments_url = pull["review_comments_url"]
    response = requests.get(comments_url, headers=headers)
    response.raise_for_status()
    comments = response.json()
    comment_messages = [comment["body"] for comment in comments]
    comment_text = "\n".join(comment_messages) if comment_messages else ""
    text += "\n" + comment_text

    # get pull commits
    commits_url = pull["commits_url"]
    response = requests.get(commits_url, headers=headers)
    response.raise_for_status()
    commits = response.json()
    commit_messages = [commit["commit"]["message"] for commit in commits]
    commit_text = "\n".join(commit_messages) if commit_messages else ""
    text += "\n" + commit_text

    return text

def get_patches(pull):
    """get gold patch and test patch"""
    patch = requests.get(pull["diff_url"]).text
    patch_test = ""
    patch_fix = ""
    for hunk in PatchSet(patch):
        if any(
                test_word in hunk.path for test_word in
                ['test', 'tests', 'testing']
        ):
            patch_test += str(hunk)
        else:
            patch_fix += str(hunk)
    return patch_fix, patch_test

def save_patch_to_file(patch_data, output_dir, file_name):
    """ save patch"""
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, file_name)
    with open(file_path, 'w') as file:
        file.write(patch_data)
    print(f'Patch data saved to {file_path}')

def save_instance_to_file(instance, output_dir, file_name):
    """ save instance"""
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, file_name)
    write_mode = "w" if not os.path.exists(file_path) else "a"
    with open(file_path, write_mode) as file:
        print(json.dumps(instance), end="\n", flush=True, file=file)
    print(f'Instance data saved to {file_path}')

def create_instance(pull):
    """ create instance """
    patch, test_patch = get_patches(pull)
    problem_statement = get_pull_commit_detail(pull)
    return {
        "repo": pull["base"]["repo"]["full_name"],
        "pull_number": pull["number"],
        "instance_id": (pull["base"]["repo"]["name"] + "-" + str(pull["number"])).replace(
            "/", "__"
        ),
        "base_commit": pull["base"]["sha"],
        "patch": patch,
        "test_patch": test_patch,
        "problem_statement": problem_statement,
        "created_at": pull["created_at"],
    }

def build_datasets(repo_owner, repo_name, pull_numbers):
    """ build datasets of patches and task instances"""
    print("Check", len(pull_numbers), "PRs for repository", os.path.join(repo_owner,repo_name))
    for pull_number in pull_numbers:
        pull = get_pull_request(repo_owner, repo_name, pull_number)
        base_commit = pull["base"]["sha"]
        patch_fix, patch_test = get_patches(pull)

        save_patch_to_file(patch_fix, os.path.join(ROOT,PATCHES_PATH), f'{repo_name}_{base_commit}_gold_patch.diff')
        save_patch_to_file(patch_test, os.path.join(ROOT, PATCHES_PATH), f'{repo_name}_{base_commit}_test_patch.diff')
        instance = create_instance(pull)
        save_instance_to_file(instance, os.path.join(ROOT, INSTANCE_PATH), f'{repo_name}-task-instances.jsonl')


def main():
    repos = ['AppFlowy-IO/AppFlowy', 'janoodleFTW/timy-messenger', 'authpass/authpass', 'gokadzev/Musify',
             'LinwoodDev/Butterfly', 'Liso-Vault/app', 'wger-project/flutter', 'xpavle00/Habo',
             'hamaluik/timecop', 'MSzalek-Mobile/weight_tracker', 'burhanrashid52/WhatTodo', 'openfoodfacts/smooth-app',
             'theachoem/spooky-mb', 'simonbengtsson/airdash', 'trizin/Quit-Smoke-App','flutter/gallery',
             'woosignal/flutter-woocommerce-app', 'theindianappguy/FlutterNewsApp', 'duytq94/flutter-chat-demo',
             'jhomlala/feather', 'JideGuru/FlutterTravel', 'JideGuru/FlutterTravel', 'abuanwar072/Quiz-App-Flutter',
             'localsend/localsend', 'KRTirtho/spotube', 'mulaRahul/keyviz', 'guozhigq/pilipala', 'wgh136/PicaComic',
             'roughike/inKino', 'harmonoid/harmonoid', 'boyan01/flutter-netease-music', 'miru-project/miru-app',
             'xujiyou/zhihu-flutter', 'LianjiaTech/bruno', 'zino-hofmann/graphql-flutter', 'letsar/flutter_staggered_grid_view',
             'OpenFlutter/fluwx', 'JideGuru/FlutterEbookApp', 'simplezhli/flutter_deer', 'TheAlphamerc/flutter_twitter_clone',
             'immich-app/immich', 'janoodleFTW/timy-messenger',
             ]
    for repo in repos[:]:
        repo_owner = repo.split('/')[0]
        repo_name = repo.split('/')[1]

        test_dir = find_test_dir(repo_owner, repo_name)
        pull_numbers = filter_pull_numbers(repo_owner, repo_name, test_dir)
        build_datasets(repo_owner, repo_name, pull_numbers)

if __name__ == '__main__':
    main()
