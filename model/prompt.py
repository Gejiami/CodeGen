def prompt_list_for_complete_file(language='flutter'):
    prompt_list = [
                ("system", '''
                    You are a ''' + language + ''' development engineer. 
                    You will be provided with a partial code base and a user's requirement statement explaining a change request.
                    <code>
                    {code_with_location}
                    </code>
                    Return the file in the format below.\n 
                    Within `<file></file>`, replace `...` with the actual name of the fixed code file.\n
                    Within `<content></content>`, replace `...` with the fixed version of the original code.
                    ```
                    # modification 1
                    <file>...</file>
                    <content>...</content>
                    # modification 2
                    <file>...</file>
                    <content>...</content>
                    # modification 3
                    ...
                    ```
                    '''),
                ("user", "<requirement>{user_instruction}<requirement>")
            ]
    return prompt_list

def prompt_list_for_diff_file(language='flutter'):
    prompt_list = [
            ("system", '''
                You are a ''' + language + ''' development engineer. 
                You will be provided with a partial code base and a user's requirement statement explaining a change request. 
                The line number of each line of every code file will be given ahead of each line. 
                <code>
                {code_with_location}
                </code>
                I need you to accomplish the provided issue by generating a single patch file that I can apply directly to this 
                repository using git apply. Please respond with a single patch file. The format should consist of changes to the code
                base, specify the file names, the line numbers of each change, and the removed and added lines. 
                A single patch file can contain changes to multiple files. 
                The line numbers should match the ones you get in the first place.
                '''),
            ("user", "<requirement>{user_instruction}<requirement>")
        ]
    return prompt_list

def prompt_list_for_position_and_patch(language='flutter'):
    prompt_list = [
        ("system", '''
            You are a ''' + language + ''' development engineer. 
            You will be provided with a partial code base and a user's requirement statement explaining a change request.
            The line number of each line of every code file will be given ahead of each line. Pay careful attention to 
            the indentation of the code when you read and generate patch.
            
            <code>
            {code_with_location}
            </code>
            
            You can import necessary libraries.\n
            Return the patch STRICTLY in the format below.\nWithin `<file></file>`, replace `...` with actual file path.\n
            Within `<position></position>`, replace `...` with the start and end line number of the modified code snippet, divided with a comma.\n
            Within `<original></original>`, replace `...` with the original code snippet modified. \n
            Within `<patched></patched>`, replace `...` with the fixed version of the original code. \n
            You should use multiple modifications if there are multiple places to be modified.  
            Think about modifications one by one.
            ```
            # modification 1
            <file>...</file>
            <position>...</position>
            <original>...</original>
            <patched>...</patched>
            # modification 2
            <file>...</file>
            <position>...</position>
            <original>...</original>
            <patched>...</patched>
            # modification 3
            ...
            ```
            '''),
            ("user", "<requirement>{user_instruction}<requirement>")
        ]
    return prompt_list

def prompt_list_for_error_message(iteration=1):
    prompt_list = [
                ("user", '''According to the chat history above, the previous code patch you generated caused an error 
                 when or before executed. Here is the error message: <error>{error_message_''' + str(iteration) +
                 '''}</error>\nReview your previous response, identify the possible cause of the error, and provide a 
                 corrected or new solution. Do not give the same solution as before. ''')
            ]
    return prompt_list

def prompt_list_for_summarize_code(language='flutter', if_code=True):
    if if_code:
        prompt_text = '''Explain the functionality of a ''' + language + '''project code snippet from code file 
                        <file_name> {file_name}</file_name>.
                        Your output must ONLY contain the explanation and not contain code. Don't bullet points or lists
                        in the explanation.
                        '''
    else:
        prompt_text = '''Explain the functionality of the file <file_name>{file_name}</file_name> 
                        of a ''' + language + ''' project.
                        Your output must ONLY contain the explanation and not contain code. Don't bullet points or lists
                        in the explanation.'''
    prompt_list = [
        ("system", prompt_text),
        ("user", "{source_code}")
    ]
    return prompt_list


def prompt_list_with_COT(language='flutter'):
    prompt_list = [
            ("system", '''
                You are a ''' + language + ''' development engineer. 
                You will be provided with a partial code base and a user's requirement statement explaining a change request.
                The line number of each line of every code file will be given ahead of each line. Pay careful attention to 
                the indentation of the code when you read and generate patch.
                <code>
                {code_with_location}
                </code>
                ### Steps
                First, carefully extract all the key words of the user's requirement or problem. 
                Then, step by step, analyze what requirements, conditions, and considerations are necessary to accurately and completely meet this need. 
                Make sure that you break down the task into clear, actionable steps to ensure a thorough and precise solution.
                ###
                You can import necessary libraries.\n
                Return the patch in the format below.\nWithin `<file></file>`, replace `...` with actual file path.\n
                Within `<position></position>`, replace `...` with the start and end line number of the modified code snippet, divided with a comma.\n
                Within `<original></original>`, replace `...` with the original code snippet modified. If there's no original code snippet, keep it as `...`\n
                Within `<patched></patched>`, replace `...` with the fixed version of the original code.
                You can write multiple modifications if needed.
                ```
                # modification 1
                <file>...</file>
                <position>...</position>
                <original>...</original>
                <patched>...</patched>
                # modification 2
                <file>...</file>
                <position>...</position>
                <original>...</original>
                <patched>...</patched>
                # modification 3
                ...
                ```
                '''),
            ("user", "<requirement>{user_instruction}<requirement>")
        ]
    return prompt_list

def prompt_list_for_process_instruction():
    prompt_list = [
        ("user", '''
        Please give step-by-step guide on how to update or modify the code to solve this issue:
        <statement>{statement}</statement>
        ''')
    ]
    return prompt_list