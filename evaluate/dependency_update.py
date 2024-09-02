import re
import os

def update_dependency_version(pubspec_file, package_name, new_version):
    with open(pubspec_file, 'r') as file:
        lines = file.readlines()

    with open(pubspec_file, 'w') as file:
        for line in lines:
            stripped_line = line.strip()
            if stripped_line.startswith(package_name + ":"):
                # keep indent
                colon_index = line.index(':')
                indent = line[:colon_index + 1]
                line = f"{indent} {new_version}\n"
            file.write(line)


def extract_dependency_info(error_log):
    dependencies = []

    pattern_1 = re.compile(
        r'\* Try upgrading your constraint on (\S+): flutter pub add (\S+:\S+)',
        re.IGNORECASE)

    pattern_2 = re.compile(
        r'because .* depends on (.+?) from .* which depends on (.+?) (.+?), (.+?) (.+?) is required\.\nSo, because .* '
        r'depends on (.+?) (.+?), version solving failed\.',
        re.IGNORECASE)

    pattern_3 = re.compile(
        r'because (.+?) >=.* depends on (.+?) from sdk which depends on (.+?) (.+?), .+? requires (.+?) (.+?)\.\nSo, '
        r'because .* depends on both (.+?) and .+?, version solving failed\.',
        re.IGNORECASE)

    matches_1 = pattern_1.findall(error_log)
    for match in matches_1:
        package_name = match[0]  # extract package name
        required_version = match[1].split(":")[1]  # extract version
        dependencies.append((package_name, required_version))

    matches_2 = pattern_2.findall(error_log)
    for match in matches_2:
        package_name = match[1]
        required_version = match[2]
        dependencies.append((package_name, required_version))

    matches_3 = pattern_3.findall(error_log)
    for match in matches_3:
        package_name = match[2]
        required_version = match[3]
        dependencies.append((package_name, required_version))

    return dependencies


def fix_dependency_collision(root_dir, error_log):
    pubspec_file = os.path.join(root_dir, "pubspec.yaml")
    dependencies = extract_dependency_info(error_log)
    if dependencies:
        for package, version in dependencies:
            print(f"Updating {package} to version {version} in {pubspec_file}")
            update_dependency_version(pubspec_file, package, version)
    else:
        print("No version conflict detected in the error log.")
