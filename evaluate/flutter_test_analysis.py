import json
import os
import re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GIT_DATASETS = os.path.join(ROOT, "git_datasets/task_instances")
PATCHES = os.path.join(ROOT, "git_datasets/filter_patches")
TEST_OUTPUT = os.path.join(ROOT, "git_datasets/flutter_test_output")
MODEL_PATCHES = os.path.join(ROOT, "git_datasets/model_patches")
MODEL_OUTPUT = os.path.join(ROOT, "git_datasets/flutter_model_output")

def print_flutter_test_output(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            print(line.strip())

def compare_test_result(repo_name, model_name="gold"):
    success = []
    files = os.listdir(TEST_OUTPUT)
    files = [file for file in files if file.split('_')[0] == repo_name]
    for file in files:
        repo_instance = '_'.join(file.split('_')[:2])
        file_post = file.split('_')[2]
        if model_name == "gold":
            if file_post == 'bf.txt' and f'{repo_instance}_af.txt' in files:
                result_bf = parse_flutter_test_output(os.path.join(TEST_OUTPUT, file))
                result_af = parse_flutter_test_output(os.path.join(TEST_OUTPUT, f'{repo_instance}_af.txt'))
            else:
                continue
        else:
            if file_post == 'bf.txt' and os.path.exists(f"{MODEL_OUTPUT}/{model_name}/{repo_instance}_af.txt"):
                result_bf = parse_flutter_test_output(os.path.join(TEST_OUTPUT, file))
                result_af = parse_flutter_test_output(f"{MODEL_OUTPUT}/{model_name}/{repo_instance}_af.txt")
            else:
                continue
        if result_bf and result_af:
            passed_bf = result_bf[-1]['passed']
            passed_af = result_af[-1]['passed']
            print(repo_instance, f'before {model_name} patch applied:', result_bf[-1])
            print(repo_instance, f'after {model_name} patch applied:', result_af[-1])
            if passed_bf < passed_af:
                print(repo_instance, 'test validation succeeded')
                success.append(repo_instance.split('_')[1])
            else:
                print(repo_instance, 'test validation failed')
        else:
            print(repo_instance, 'test result empty')
    return success


def parse_flutter_test_output(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    test_results = []
    for line in lines:
        # Match lines with test results, including '-' and '~'
        match = re.match(r"(\d{2}:\d{2}) \+(\d+)( ~\d+)?( -\d+)?: (.+)", line)
        if match:
            time = match.group(1)
            passed = match.group(2)
            skipped = match.group(3).strip().replace('~', '') if match.group(3) else 0
            failed = match.group(4).strip().replace('-', '') if match.group(4) else 0
            description = match.group(5)

            # Check if the description includes an error
            if 'Error:' in description:
                error_match = re.search(r'Error: (.+)', description)
                error_message = error_match.group(1) if error_match else 'Unknown error'
                test_results.append({
                    'time': time,
                    'passed': passed,
                    'skipped': skipped,
                    'failed': failed,
                    'description': description.split('Error:')[0].strip(),
                    'error': error_message
                })
            else:
                test_results.append({
                    'time': time,
                    'passed': passed,
                    'skipped': skipped,
                    'failed': failed,
                    'description': description,
                    'error': None
                })

    return test_results

def print_parsed_test_results(test_results):
    for result in test_results:
        print(f"Time: {result['time']}")
        print(f"Passed: {result['passed']}")
        print(f"Skipped: {result['skipped']}")
        print(f"Failed: {result['failed']}")
        print(f"Description: {result['description']}")
        if result['error']:
            print(f"Error: {result['error']}")

def compare_gold_and_model(repo_name, model_name):
    model_path = f"{MODEL_OUTPUT}/{model_name}"
    # model_outputs = [os.path.join(model_path, file) for file in os.listdir(model_path) if file.startswith(repo)]
    commits = [file.split('_')[1] for file in os.listdir(model_path) if file.startswith(repo_name)]
    gold_path = TEST_OUTPUT

    for commit in commits:
        if os.path.exists(f"{gold_path}/{repo_name}_{commit}_af.txt") \
            and os.path.exists(f"{gold_path}/{repo_name}_{commit}_bf.txt"):
            task_instances = []
            with open(f"{GIT_DATASETS}/{repo_name}-task-instances.jsonl", 'r') as file:
                for line in file:
                    try:
                        task_instances.append(json.loads(line.strip()))
                    except json.JSONDecodeError as e:
                        print(f"JSONDecodeError: {e} for line: {line}")
            for task_instance in task_instances:
                if task_instance["base_commit"] == commit:
                    print("user_instruction:\n", task_instance['problem_statement'])
                    break

            result_bf = parse_flutter_test_output(f"{gold_path}/{repo_name}_{commit}_bf.txt")
            result_gold = parse_flutter_test_output(f"{gold_path}/{repo_name}_{commit}_af.txt")
            result_model = parse_flutter_test_output(f"{MODEL_OUTPUT}/{model_name}/{repo_name}_{commit}_af.txt")
            if result_bf and result_gold and result_model:
                print(repo_name, commit, f'before any patch applied:', result_bf[-1])
                print(repo_name, commit, f'after gold patch applied:', result_gold[-1])
                print(repo_name, commit, f'after model patch applied:', result_model[-1])

                with open(f"{PATCHES}/{repo_name}_{commit}_test_patch.diff", "r") as f:
                    test_patch = f.read()
                with open(f"{PATCHES}/{repo_name}_{commit}_gold_patch.diff", "r") as f:
                    gold_patch = f.read()
                with open(f"{MODEL_PATCHES}/{model_name}/{repo_name}_{commit}_model_patch.diff", "r") as f:
                    model_patch = f.read()

                print("test patch:\n", test_patch)
                print("gold patch:\n", gold_patch)
                print("model patch:\n", model_patch)

