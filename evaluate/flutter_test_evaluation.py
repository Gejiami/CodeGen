import os
import subprocess
import json
import datetime

from evaluate.flutter_test_analysis import compare_test_result
from task.run_task import LLMCodeGenerator
from flutter_version_manage import manage_flutter_version

HOME = os.getenv('HOME')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GIT_DATASETS = os.path.join(ROOT, "git_datasets/task_instances")
PATCHES = os.path.join(ROOT, "git_datasets/filter_patches")
TEST_OUTPUT = os.path.join(ROOT, "git_datasets/flutter_test_output")
MODEL_PATCHES = os.path.join(ROOT, "git_datasets/model_patches")
MODEL_OUTPUT = os.path.join(ROOT, "git_datasets/flutter_model_output")
LOGS = os.path.join(HOME, "git_datasets/logs")

FLUTTER = os.path.join(HOME, "flutter/bin/flutter")
ROOT_MAP = {"AppFlowy-IO/AppFlowy": f"{HOME}/AppFlowy/frontend/appflowy_flutter",
            "openfoodfacts/smooth-app": f"{HOME}/smooth-app/packages/smooth_app",
            "immich-app/immich": f"{HOME}/immich/mobile",
            "localsend/localsend": f"{HOME}/localsend/app",
            "LianjiaTech/bruno": f"{HOME}/bruno",
            "theachoem/spooky-mb": f"{HOME}/spooky-mb",
            "duytq94/flutter-chat-demo": f"{HOME}/flutter-chat-demo",
            "flutter/gallery":f"{HOME}/gallery"}


def find_task_instance_files(directory):
    task_instance_files = []
    # Walk through the directory
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith("task-instances.jsonl"):
                if file=='flutter-task-instances.jsonl':
                    continue
                file_path = os.path.join(root, file)
                # Check if the file size is greater than zero
                if os.path.getsize(file_path) > 0:
                    task_instance_files.append(file_path)

    return task_instance_files


def read_task_instances(file_path):
    task_instances = []
    with open(file_path, 'r') as file:
        for line in file:
            # parse json
            try:
                task_instances.append(json.loads(line.strip()))
            except json.JSONDecodeError as e:
                print(f"JSONDecodeError: {e} for line: {line}")
    return task_instances


def git_clone_repo(repo, overwrite=False):
    os.chdir(HOME)
    proj = '/'.join(repo.split('/')[1:])
    # git clone
    if not os.path.exists(proj):
        subprocess.run(["git", "clone", f"https://github.com/{repo}.git", proj], check=True)
    else:
        if overwrite:
            subprocess.run(["rm", "-rf", proj], check=True)
            subprocess.run(["git", "clone", f"https://github.com/{repo}.git", proj], check=True)
    print(f"Repo {repo} cloned successfully")

def pub_get_dependencies(task_instance):
    repo = task_instance['repo']
    base_commit = task_instance['base_commit']
    root_dir = ROOT_MAP[repo]

    # change to repo root dir
    os.chdir(root_dir)
    # cancel change

    subprocess.run(["git", "restore", "--staged", "."], check=True)
    subprocess.run(["git", "restore", "."], check=True)
    subprocess.run(["git", "clean", "-fd"], check=True)
    # checkout commit
    subprocess.run(["git", "checkout", base_commit], check=True)

    # install and switch flutter version
    manage_flutter_version(ROOT_MAP[repo], 'use')


def validate_task_instance(task_instance, log_dir='gold'):
    repo = task_instance['repo']
    proj = '/'.join(repo.split('/')[1:])
    base_commit = task_instance['base_commit']
    patch = task_instance['patch']
    test_patch = task_instance['test_patch']
    root_dir = ROOT_MAP[repo]
    # change to repo root dir
    os.chdir(root_dir)
    env = os.environ.copy()
    input_data = "y\ny\ny\ny\n"
    env["PATH"] += os.pathsep + os.path.expanduser(f"{HOME}/.pub-cache/bin")
    env["PATH"] += os.pathsep + os.path.expanduser(f"{HOME}/flutter/bin")
    # print(env["PATH"])
    print('Current path:', os.getcwd())

    if log_dir == 'gold':
        # apply test patch
        with open(f"{PATCHES}/{proj}_{base_commit}_test_patch.diff", "w") as test_patch_file:
            test_patch_file.write(test_patch)
        subprocess.run(["git", "apply", f"{PATCHES}/{proj}_{base_commit}_test_patch.diff"], check=True)

        process = subprocess.Popen("fvm flutter test", shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, env=env)
        try:
            stdout, stderr = process.communicate(input=input_data, timeout=120)
            with open(f"{TEST_OUTPUT}/{proj}_{base_commit}_bf.txt", "w") as output_file:
                output_file.write(stdout.strip())
            print(f"Test output before applying patch saved to {TEST_OUTPUT}/{proj}_{base_commit}_bf.txt")
        except subprocess.TimeoutExpired:
            process.kill()
            print("The command timed out.")
        except subprocess.CalledProcessError as e:
            print(f"Command failed with exit code {e.returncode}")
        except Exception as e:
            print(f"An error occurred: {e}")

        # apply gold patch
        with open(f"{PATCHES}/{proj}_{base_commit}_gold_patch.diff", "w") as patch_file:
            patch_file.write(patch)
        subprocess.run(["git", "apply", f"{PATCHES}/{proj}_{base_commit}_gold_patch.diff"], check=True)

        # test result after applying gold patch
        process = subprocess.Popen("fvm flutter test", shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, env=env)
        try:
            stdout, stderr = process.communicate(input=input_data, timeout=120)
            with open(f"{TEST_OUTPUT}/{proj}_{base_commit}_af.txt", "w") as output_file:
                output_file.write(stdout.strip())
            print(f"Test output after applying patch saved to {TEST_OUTPUT}/{proj}_{base_commit}_af.txt")
        except subprocess.TimeoutExpired:
            process.kill()
            print("The command timed out.")
        except subprocess.CalledProcessError as e:
            print(f"Command failed with exit code {e.returncode}")
        except Exception as e:
            print(f"An error occurred: {e}")
    else:
        if os.path.exists(f"{MODEL_PATCHES}/{log_dir}/{proj}_{base_commit}_model_patch.diff"):
            if not os.path.exists(os.path.join(MODEL_OUTPUT, log_dir)):
                # create dir
                os.makedirs(os.path.join(MODEL_OUTPUT, log_dir))

            # apply test patch
            with open(f"{PATCHES}/{proj}_{base_commit}_test_patch.diff", "w") as test_patch_file:
                test_patch_file.write(test_patch)
            subprocess.run(["git", "apply", f"{PATCHES}/{proj}_{base_commit}_test_patch.diff"], check=True)

            process = subprocess.Popen("fvm flutter test", shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, env=env)
            try:
                stdout, stderr = process.communicate(input=input_data, timeout=120)
                with open(f"{TEST_OUTPUT}/{proj}_{base_commit}_bf.txt", "w") as output_file:
                    output_file.write(stdout.strip())
                print(f"Test output before applying patch saved to {TEST_OUTPUT}/{proj}_{base_commit}_bf.txt")
            except subprocess.TimeoutExpired:
                process.kill()
                print("The command timed out.")
            except subprocess.CalledProcessError as e:
                print(f"Command failed with exit code {e.returncode}")
            except Exception as e:
                print(f"An error occurred: {e}")

            # apply model patch
            print(f"{MODEL_PATCHES}/{log_dir}/{proj}_{base_commit}_model_patch.diff")
            print('Model patch found:', base_commit)
            subprocess.run(["git", "apply", f"{MODEL_PATCHES}/{log_dir}/{proj}_{base_commit}_model_patch.diff"], check=True)

            # test result after applying model patch
            process = subprocess.Popen("fvm flutter test", shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, env=env)
            try:
                stdout, stderr = process.communicate(input=input_data, timeout=120)

                with open(f"{MODEL_OUTPUT}/{log_dir}/{proj}_{base_commit}_af.txt", "w") as output_file:
                    output_file.write(stdout.strip())
                print(f"Test output after applying patch saved to {TEST_OUTPUT}/{proj}_{base_commit}_af.txt")
            except subprocess.TimeoutExpired:
                process.kill()
                print("The command timed out.")
            except subprocess.CalledProcessError as e:
                print(f"Command failed with exit code {e.returncode}")
            except Exception as e:
                print(f"An error occurred: {e}")
        else:
            return

    # cancel change
    subprocess.run(["git", "restore", "--staged", "."], check=True)
    subprocess.run(["git", "restore", "."], check=True)
    subprocess.run(["git", "clean", "-fd"], check=True)
    print("git status:")
    subprocess.run(["git", "status"])
    # remove flutter version
    manage_flutter_version(root_dir, 'remove')

def test_gold_patch():
    # read git datasets
    task_instance_files = find_task_instance_files(GIT_DATASETS)
    for file in task_instance_files:
        print(file)
    for file in task_instance_files[:]:
        task_instances = read_task_instances(file)
        for task_instance in task_instances[:]:
            # print(task_instance)
            git_clone_repo(task_instance['repo'])
            flutter_version = pub_get_dependencies(task_instance)
            try:
                validate_task_instance(task_instance)
            except Exception as e:
                print("Validation error:")
                print(e)

def generate_model_patch(repo, log_dir, model_name="gpt-4o-mini"):
    if not os.path.exists(os.path.join(MODEL_PATCHES, log_dir)):
        # create dir
        os.makedirs(os.path.join(MODEL_PATCHES, log_dir))

    task_instance_files = find_task_instance_files(GIT_DATASETS)
    # for file in task_instance_files:
    #     print(file)
    git_clone_repo(repo, False)
    for file in task_instance_files[:]:
        repo_name = repo.split('/')[1]
        project_name = file.split('/')[-1].replace('-task-instances.jsonl', '')
        passed = compare_test_result(project_name)
        if repo_name == project_name:
            task_instances = read_task_instances(file)
            last_commit = None
            for task_instance in task_instances[:]:
                # create model patch
                start_time = datetime.datetime.now()
                model_patch = ''
                project_name = task_instance['repo'].split('/')[1]
                base_commit = task_instance['base_commit']

                print(passed)
                if base_commit not in passed:
                    continue
                print(project_name, base_commit, datetime.datetime.now())
                user_instruction = task_instance['problem_statement']
                print(user_instruction)
                generator = LLMCodeGenerator(language='flutter', project_name=project_name, project_path=HOME,
                                             user_instruction=user_instruction, sha=base_commit, model_name=model_name)
                try:
                    refresh = True if not last_commit else False
                    generator.set_vector_store(refresh=False, update_from_sha=last_commit)
                    matched_docs, all_success, all_message = generator.generate_patch()
                    print(all_success)
                    model_patch = generator.create_git_diff()
                    print(model_patch)
                    token_usage = generator.llm.token_usage
                    end_time = datetime.datetime.now()
                    task_instance["token_usage"] = token_usage
                    task_instance["model_patch"] = model_patch
                    task_instance["model_name"] = model_name
                    task_instance["run_time"] = (end_time - start_time).total_seconds()
                    task_instance["matched_docs"] = str(matched_docs)
                    task_instance["log_message"] = all_message
                    task_instance["success"] = all_success
                    task_instance["llm_instruction"] = generator.user_instruction
                except Exception as e:
                    print("ERROR:", e)

                generator.restore_git_files()
                last_commit = base_commit
                # save model patch
                with open(os.path.join(MODEL_PATCHES, log_dir, f'{project_name}_{base_commit}_model_patch.diff'),'w', encoding='utf-8') as f:
                    f.write(model_patch)
                print('Model diff patch saved', datetime.datetime.now())
                #save log
                if not os.path.exists(os.path.join(LOGS, log_dir)):
                    os.mkdir(os.path.join(LOGS, log_dir))
                with open(os.path.join(LOGS, log_dir, f'{project_name}_{base_commit}_log.json'),'w', encoding='utf-8') as f:
                    json.dump(task_instance, f)
                print('Model log saved', datetime.datetime.now())


def test_model_patch(log_dir="gpt4omini"):
    # read git datasets
    task_instance_files = find_task_instance_files(GIT_DATASETS)
    for file in task_instance_files:
        print(file)
    for file in task_instance_files[:]:
        if 1:
            task_instances = read_task_instances(file)
            for task_instance in task_instances[:]:
                # print(task_instance)
                base_commit = task_instance['base_commit']
                repo = task_instance['repo']
                proj = '/'.join(repo.split('/')[1:])
                print(f"{MODEL_PATCHES}/{log_dir}/{proj}_{base_commit}_model_patch.diff")
                if os.path.exists(f"{MODEL_PATCHES}/{log_dir}/{proj}_{base_commit}_model_patch.diff"):
                    print("match model patch:", repo, base_commit)
                    git_clone_repo(repo)
                    flutter_version = pub_get_dependencies(task_instance)
                    try:
                        validate_task_instance(task_instance, log_dir)
                    except Exception as e:
                        print("Validation error:")
                        print(e)