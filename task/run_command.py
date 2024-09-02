import os
import subprocess

HOME = os.getenv('HOME')

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