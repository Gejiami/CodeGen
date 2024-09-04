import openai
from langchain_core.prompts import ChatPromptTemplate
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from langchain_openai import ChatOpenAI

from model.output_parser import FileOutputParser
from model.prompt import prompt_list_for_error_message

MAX_RETRY = 3
RETRY_WAIT_TIME = 30


class Openai:
    def __init__(self, api_key, model_name="gpt-4o-mini", temperature=0.1, top_p=1):
        self.chain = None
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.top_p = top_p
        self.model = ChatOpenAI(
            model=self.model_name,
            openai_api_key=self.api_key,
            temperature=self.temperature,
            top_p=self.top_p
        )
        self.prompt_list_history = []
        self.input_dict_history = {}
        self.token_usage = 0

    @retry(
        retry=retry_if_exception_type(openai.RateLimitError),
        stop=stop_after_attempt(MAX_RETRY),
        wait=wait_fixed(RETRY_WAIT_TIME)
    )
    def invoke(self, prompt_list, input_dict, output_parser=FileOutputParser(), record=True):
        prompt = ChatPromptTemplate.from_messages(prompt_list)
        if record:
            self.prompt_list_history = prompt_list
            self.input_dict_history = input_dict
        chain = prompt | self.model
        try:
            response = chain.invoke(input_dict)
            self.token_usage += response.response_metadata["token_usage"]["total_tokens"]
            if output_parser:
                response = output_parser.parse(response.content)
            if record:
                self.prompt_list_history.append(("ai", "<parsed_ai_response>{ai_response_1}</parsed_ai_response>"))
                self.input_dict_history["ai_response_1"] = str(response)
            return response
        except openai.AuthenticationError as auth_err:
            print(f"Authentication failed: {str(auth_err)}")
        except openai.NotFoundError as not_found_err:
            print(f"Model not found or access denied: {str(not_found_err)}")
            print("You can try model names like 'gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo-16k' etc.")
        except openai.RateLimitError as e:
            print(f"Rate limit error: {e}. Retrying in {RETRY_WAIT_TIME} seconds.")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

    def iterate(self, error_message, iteration_number, output_parser=FileOutputParser()):
        error_prompt_list = prompt_list_for_error_message(iteration=iteration_number)
        self.prompt_list_history = self.prompt_list_history + error_prompt_list
        prompt = ChatPromptTemplate.from_messages(self.prompt_list_history)
        self.input_dict_history[f'error_message_{iteration_number}'] = error_message
        chain = prompt | self.model
        try:
            response = chain.invoke(self.input_dict_history)
            self.token_usage += response.response_metadata["token_usage"]["total_tokens"]
            if output_parser:
                response = output_parser.parse(response.content)
            self.prompt_list_history.append(("ai", '''<parsed_ai_response>{ai_response_''' + str(iteration_number+1) +
                                             '''}</parsed_ai_response>'''))
            self.input_dict_history[f'ai_response_{iteration_number+1}'] = str(response)
            return response
        except openai.AuthenticationError as auth_err:
            print(f"Authentication failed: {str(auth_err)}")
        except openai.NotFoundError as not_found_err:
            print(f"Model not found or access denied: {str(not_found_err)}")
            print("You can try model names like 'gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo-16k' etc.")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

