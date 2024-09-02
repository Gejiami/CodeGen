from task.run_task import main

main(home_path='/home/azureuser',
     repo='talk_with',
     repo_type='local',
     language='flutter',
     commit_sha=None,
     last_commit_sha=None,
     model_name='gpt-4o',
     user_instruction=
     '''Exchange the position of ALL the contents about "job loss" and "pet death" in "talk with insight" page.
     '''
     ,
     log_dir='/home/azureuser/log')

