import os
import re
import json
import datetime
from inspect import cleandoc

from ollama import Client
from tavily import TavilyClient


# 
# Agent core
#
class RunawayResponse(Exception): 
    pass

class InvalidResponseFormat(Exception): 
    pass

class InvalidActionInput(Exception): 
    pass


class Agent:
    """A simple AI agent that can answer questions by planning and performing multiple steps"""

    def __init__(self, host: str, model: str, tools: list | None = None):
        """
        Instantiate an agent
        Provide a model name and (optionally) a list of tools
        """
        tools = [answer] + (tools or []) # Always have access to 'answer'
        self.known_actions = {tool.__name__: tool for tool in tools}
        self.client = Client(host)
        self.model = model
        self.system_message = gen_sysprompt(tools)
        # print(f"====\n{self.system_message}\n====")
        self.messages = [{"role":"system", "content": self.system_message}]


    def task(self, user_query: str, max_steps: int = 10):
        """Public interface"""
        return self._perform_steps(user_query, max_steps)

    def _perform_steps(self, step_input: str, max_steps: int):
        """
        Repeatedly plan (reason) and act (call tools) until user's question can (or can't) be answered.
        Return an answer or a statement that an answer cannot be given.
        Return an error message if a conclusion cannot be reached in maximum number of steps (default 10)
        """
        i = 0

        while i < max_steps:
            i += 1
            print(f"Step #{i}")

            response = self._chat(step_input)
            try:
                action, action_input = parse_response(response)
            except RunawayResponse:
                print("Runaway response, let's pretend it never happened...")
                # Delete two last entries in message history
                _ = self.messages.pop() # Bad resonse
                _ = self.messages.pop() # Input that will be retried
                print(f"---- Discarding:\n{response}\n----")
                continue # Loop again
            except InvalidResponseFormat:
                step_input = "Observation: Error: Invalid response format"
                continue # Loop again
            except InvalidActionInput:
                step_input = "Observation: Error: Invalid Action Input format"
                continue # Loop again
                     
            if action not in self.known_actions: # Check that we have that tool...
                step_input = f"Observation: Error: Invalid action ({action})"
                continue # Loop again

            try:
                print(f"Using tool '{action}'...")
                result = self.known_actions[action.strip()](**action_input)
                step_input = f"Observation: {result}" # Feed back result of tool call
            except:
                step_input = f"Observation: Error: There was a problem using the tool ('{action}') with the given input."
               
            if action == answer.__name__:
                return result # Done

        # We hit the maximum number of steps, the LLM is likely very confused
        return f"Agent was unable to answer your question in the maximal number of steps ({max_steps})"

    def _chat(self, message: str):
        """Process a message and return a response"""

        print("just a moment ...")

        self.messages.append({"role": "user", "content": message})

        response = self.client.chat(
            model=self.model,
            messages=self.messages,
            options={"num_ctx": 32768}
        )
        text = response.message.content

        # Store assistant's response in short-term memory
        self.messages.append({"role": "assistant", "content": text})
        return text

    #
    # Debugging helper
    #
    def message_history(self):
        """
        Return a description of the steps taken to arrive at the answer (excluding system prompt).
        """
        return "\n".join([f"**{msg['role']}**:\n{msg['content']}\n" for msg in self.messages[1:]])

#
# Parse Response
#
def parse_response(response) -> (str, dict):
    """
    Parse the LLM response to extract action and action input.
    """    
    # Capture tool name following 'Action:'
    RE_ACTION = re.compile(r'^Action:\s*([_a-zA-Z][_a-zA-Z0-9]*)', re.MULTILINE)
    # Capture JSON following 'Action Input:'
    RE_ACTION_INPUT = re.compile(r'^Action Input:\s*({.*})', re.MULTILINE | re.DOTALL)

    # Try to detect eagerness, i.e. 'Observation:' in (runaway) response
    RE_OBSERVATION = re.compile(r'Observation:', re.MULTILINE)
    if RE_OBSERVATION.search(response) is not None:
        raise RunawayResponse
    
    action_match = RE_ACTION.findall(response)
    input_match = RE_ACTION_INPUT.findall(response)

    if len(action_match) == 0 or len(action_match) == 0:
        raise InvalidResponseFormat
        
    if len(action_match) > 1 or len(action_match) > 1:
        # Multiple 'Action:' or 'Action Input:' lines means we have a runaway response
        raise RunawayResponse

    # Get the first response    
    action = action_match[0]
    action_input_string = input_match[0]
    
    try:
        # Convert action input from JSON to python dict
        action_input = json.loads(action_input_string)
    except:
        # The response was properly structured, but the action_input was not valid JSON
        raise InvalidActionInput
    
    return (action, action_input)
#
# System prompt
#
def gen_sysprompt(tools: list | None = None) -> str:
    tools = tools or []
    tools.append(answer) # The answer tool is always avilable
    
    preamble = sysprompt_preamble()
    tool_info = sysprompt_tools(tools)
    instructions = sysprompt_react_instructions()

    return f"{preamble}\n\n{tool_info}\n\n{instructions}\n\n"

def sysprompt_preamble() -> str:
    return cleandoc("""
        You are an assistant that breaks down problems into multiple, simple steps and solves them systematically.
        You have access to tools defined in the 'Tools' section.
        ALWAYS prefer using tools to relying on your general knowledge, e.g. if you have access to a calcuator ALWAYS use it to evaluate formulas.

        """)

def sysprompt_tools(tools: list) -> str:

    preamble = """
        ## Tools
        
        You are responsible for using the tools in any sequence you deem appropriate to complete the task at hand.
        This may require breaking the task into subtasks and using different tools to complete each subtask.

        You have access to the following tools:

        """

    docs = [cleandoc(preamble)]
    for tool in tools:
        tool_name = tool.__name__
        tool_doc = cleandoc(tool.__doc__)
        docs.append(f"\n> Tool Name: {tool_name}\n{tool_doc}\n")

    return "\n".join(docs)

def sysprompt_react_instructions() -> str:
    instructions = """
        ## Output Format

        ALWAYS use the following format in your response (EXACTLY one each of 'Thought:', 'Action:' and 'Action Input:'):

        ```
        Thought: [your current thought]
        Action: [tool name]
        Action Input: [the input to the tool, in JSON format representing the kwargs (e.g. {"input": "hello world", "num_beams": 5})]
        ```

        Please communicate in the same language as the question and use ONLY one of the following three alternatives:

        1. If you need more information to answer the question:

        ```
        Thought: I need to use a tool to help me answer the question.
        Action: [tool name]
        Action Input: [the input to the tool, in JSON format representing the kwargs (e.g. {"input": "hello world", "num_beams": 5})]
        ```

        2. If you have enough information to answer the question:

        ```
        Thought: I can answer without using any more tools.
        Action: answer
        Action Input: [your answer, in JSON format (e.g. {"reply": "OK"})]
        ```

        3. If you cannot answer the question even after using tools to retrieve more information:

        ```
        Thought: I cannot answer the question with the provided tools.
        Action: answer
        Action Input: [your answer, in JSON format (e.g. {"reply": "Sorry"})]
        ```

        ALWAYS start with a Thought followed by an Action and finally an Action Input.
        NEVER surround your response with markdown code markers.

        If you decide that a tool other than 'answer' is required, the result will be reported in the following form:

        ```
        Observation: [tool use result (e.g. 'Stockholm') or an error message (e.g. 'Error: Invalid input') in case of failure]
        ```

        Use JSON formatted data for the Action Input argument, e.g. {"input": "hello world", "num_beams": 5}.
        ALWAYS use a dictionary as the root object in JSON data.
        If the tool does not require any input, you MUST provide an empty dictionary as action input, i.e. "Action Input: {}".
        NEVER continue after completing the Action Input argument.

        You should keep repeating the above steps until you have enough information to answer without using any more tools. At that point, you MUST respond in using format 2 or 3.


        ## Current Conversation

        Below is the current conversation consisting of interleaving user and assistant messages.

        """

    return cleandoc(instructions)

#
# Tools
#

def answer(reply: str) -> str:
    """
    Conveys your final reply to the user

    Args:
        reply (str): Your final reply to the user

    Returns:
        str: echoes 'reply'

    """
    return reply
    
def date() -> str:
    """
    Reports the current date and time

    Args:
        None

    Returns:
        str: a string with the date and time in ISO 8601 format
    """
    now = datetime.datetime.now()
    datestr = now.strftime("%Y-%m-%dT%H:%M")
    # return "Error: Tool unavailable" # Test error handling
    return datestr


def calculator(expression: str) -> str:
    """
    Performs basic mathematical calculations, use also for simple additions

    Args:
        expression (str): The mathematical expression to evaluate (e.g., '2+2', '10*5')

    Returns:
        str: the result of the evaluation or an error message in case of failure
    """
    try:
        result = eval(expression)
        return str(result)
    except:
        return "Error: Invalid mathematical expression"


def web_search(query: str) -> dict:
    """
    Performs a web search using the Tavily API.
    This function initializes a Tavily client with an API key and performs a search query using their search engine. Tavily specializes in providing AI-optimized search results with high accuracy and relevance.

    Args:
        query (str): The search query string to be processed by Tavily's search engine.

    Returns:
        dict: A dictionary containing the search result from Tavily. The dicionary contain:
            - url: The URL of the webpage
            - content: A snippet or content preview

    """
    API_KEY = os.environ.get('TAVILY_API_KEY', "")
    if API_KEY == "": return "Error: Tool unavailable (API_KEY missing)"

    client = TavilyClient(api_key=API_KEY)
    # Pick out a single hit
    raw_results = client.search(query)
    top_result = raw_results['results'][0]
    
    return {'url': top_result['url'], 'content': top_result['content']}
