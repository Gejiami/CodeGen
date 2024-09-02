import os
import subprocess

from bs4 import BeautifulSoup
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE_PATH = ROOT

import re
from packaging import version

# extract Dart and Flutter version from pubspec.lock
def extract_version_ranges(content):
    dart_range_match = re.search(r'dart:\s*"([^"]+)"', content)
    flutter_range_match = re.search(r'flutter:\s*"([^"]+)"', content)
    dart_range = dart_range_match.group(1) if dart_range_match else ""
    flutter_range = flutter_range_match.group(1) if flutter_range_match else ""
    return dart_range, flutter_range

def parse_version_range(version_range):
    if not version_range:
        return (None, None)

    parts = version_range.split(' ')
    min_version = max_version = None

    for part in parts:
        if part.startswith('>='):
            min_version = part[2:]
        elif part.startswith('<'):
            max_version = part[1:]

    return min_version, max_version

def parse_valid_version(version_str):
    if not version_str:
        version_str = ''
    try:
        v = version.parse(version_str)
        return v
    except Exception as e:
        match = re.match(r'^(\d+\.\d+\.\d+)', version_str)
        if match:
            return version.parse(match.group(1))
        else:
            return None

def is_version_in_range(version_str, min_version, max_version):
    v = parse_valid_version(version_str)
    min_v = parse_valid_version(min_version)
    max_v = parse_valid_version(max_version)

    if min_v and v < min_v:
        return False
    if max_v and v >= max_v:
        return False

    return True

# filter valid Flutter versions
def find_matching_flutter_version(root_dir):
    # 从 pubspec.lock 提取版本范围
    versions = read_dart_flutter_version()
    pubspec_lock_content = read_pubspec_lock(root_dir)
    dart_range, flutter_range = extract_version_ranges(pubspec_lock_content)
    dart_min, dart_max = parse_version_range(dart_range)
    flutter_min, flutter_max = parse_version_range(flutter_range)
    matching_min_flutter_version = max(versions.keys())
    for flutter_version, dart_version in versions.items():
        if is_version_in_range(flutter_version, flutter_min, flutter_max) and is_version_in_range(dart_version,
                                                                                                  dart_min, dart_max):
            matching_min_flutter_version = min(flutter_version, matching_min_flutter_version)
    return matching_min_flutter_version

def read_dart_flutter_version():
    with open(f'{VERSION_FILE_PATH}/dart_flutter_versions.html', 'r', encoding='utf-8') as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.select_one('#downloads-linux-stable')

    # check table
    if table:
        # initialize dict
        versions = {}

        rows = table.select('tr')
        for row in rows:
            tds = row.find_all('td')
            if len(tds) >= 5:
                flutter_cell = tds[0].select_one('a')
                dart_cell = tds[4].select_one('span')

                if flutter_cell and dart_cell:
                    flutter_version = flutter_cell.text.strip()
                    dart_version = dart_cell.text.strip()
                    if dart_version != '-':
                        versions[flutter_version] = dart_version

        return versions
    else:
        print("Table with ID 'downloads-linux-stable' not found.")

def read_pubspec_lock(root_dir):
    # check pubspec.lock file exists
    pubspec_lock_path = os.path.join(root_dir, 'pubspec.lock')
    if not os.path.isfile(pubspec_lock_path):
        raise ValueError(f"No pubspec.lock file found in the provided project root '{root_dir}'.")
    file_path = os.path.join(root_dir, 'pubspec.lock')
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def manage_flutter_version(root_dir, type='use'):
    # switch root
    flutter_version = find_matching_flutter_version(root_dir)
    print("Matching Flutter version:", flutter_version)

    # switch flutter version with fvm
    os.chdir(root_dir)
    env = os.environ.copy()
    env["PATH"] += os.pathsep + os.path.expanduser("~/.pub-cache/bin")
    env["PATH"] += os.pathsep + os.path.expanduser("~/flutter/bin")
    # print(env["PATH"])
    print('Current path:', os.getcwd())

    # type : use or remove
    command = f"fvm {type} {flutter_version}"

    input_data = "y\ny\ny\ny\n"
    # create Popen
    process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, env=env)
    try:
        stdout, stderr = process.communicate(input=input_data, timeout=120)
        print("stdout:", stdout.strip())
        return flutter_version
    except subprocess.TimeoutExpired:
        process.kill()
        print("The command timed out.")
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
    except Exception as e:
        print(f"An error occurred: {e}")
