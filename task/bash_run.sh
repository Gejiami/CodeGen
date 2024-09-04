#!/usr/bin/env bash

#python .run_task.py \
#    --repo 'talk_with' \
#    --repo_type 'local' \
#    --language 'flutter' \
#    --home_path '/home/azureuser' \
#    --log_dir '/home/azureuser/log' \
#    --model_name 'gpt-4o' \
#    --user_instruction '''
#    Add a half white line underneath the introductions in all Talk with Empathy sections. (the introduction is the content before the side letters begin).
#    ''' \

python ./run_task.py --repo 'Gejiami/flutter_test' --repo_type 'github' --language 'flutter' --model_name 'gpt-4o'  --user_instruction '''Increase the size of the text box on the home page.'''
