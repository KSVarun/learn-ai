import asyncio
from fastapi import FastAPI, WebSocket
from langchain_community.chat_models import ChatOllama
from langchain_core.runnables import RunnablePassthrough
from atlassian import Jira
from dotenv import load_dotenv
import os
import pandas as pd
from operator import itemgetter
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import HumanMessage
import datetime
from langchain_core.messages import SystemMessage


load_dotenv()

model="llama3.1:8b-instruct-q8_0"
llm = ChatOllama(model=model, temperature=0)

app = FastAPI()


# @app.get("/")
# async def root():
#     return {"message": "asdf     World"}

# @app.get("/")
# async def get():
#     return HTMLResponse(html)


# try:
#     jira = Jira(
#     url=os.getenv("url"),
#     username=os.getenv("username"),
#     password=os.getenv("password"),
#     cloud=True)
# except Exception as e:
#     print(f"Unable to login to jira, Error: {e}")

def createJiraTaskFromLocalCSVFile(csvPath:str):
    df = pd.read_csv(csvPath)
    created_jira = []
    for index, row in df.iterrows():
        if pd.notna(row['summary']) and pd.isna(row['jira']):
            fields = {'project':{'key':'AN30'},'issuetype': {'name': 'Task'},'summary': row['summary'], 'description':row['description'], 'assignee':{'id':row['assignee']}}

            # jira_issue_response will contain {'id': '2784859', 'key': 'AN30-6067', 'self': 'link to the json response'}
            # jira_issue_response=jira.issue_create(fields)
            # updated_jira_issue_response=jira_issue_response
            # updated_jira_issue_response['title']=row['summary']
            # created_jira.append(updated_jira_issue_response)
            # df.at[index, 'jira'] = f'https://amagiengg.atlassian.net/browse/{jira_issue_response['key']}'
    df.to_csv(csvPath, index=False)
    return created_jira

store = {}

def get_valid_functions():
    return ['createJiraTaskFromLocalCSVFile']

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

def connectToLLama():
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                You are a highly capable AI assistant tasked with understanding user queries and responding with the appropriate function from the list provided below. Your response must adhere to the following constraints:

                Functions:
                    - createJiraTaskFromLocalCSVFile(pathToCSV)

                Constraints:
                    - Only use the functions listed above. Do not generate or suggest any other functions.
                    - Ensure that the function you generate directly addresses the query made by the user.
                    - If the query does not correspond to any function you are allowed to use, respond with an empty string ''.
                    - Include only the function name and arguments in your response, without any additional text.

                Examples:
                    - Query: "Can you read the csv in the path '../csvFiles/jira_task_list.csv' and create jira for each items" 
                    Response: "createJiraTaskFromLocalCSVFile('../csvFiles/jira_task_list.csv')"
                    - Query: "read the csv in the path '../csvFiles/jira_task_list.csv' and create jira for each items" 
                    Response: "createJiraTaskFromLocalCSVFile('../csvFiles/jira_task_list.csv')"
                    - Query: "get the data from the csv in the path '../csvFiles/jira_task_list.csv' and create jira for each items" 
                    Response: "createJiraTaskFromLocalCSVFile('../csvFiles/jira_task_list.csv')"
                    - Query: "from the csv in the path '../csvFiles/jira_task_list.csv' get the data and create jira for each items" 
                    Response: "createJiraTaskFromLocalCSVFile('../csvFiles/jira_task_list.csv')"
                    - Query: "csv read jira '../csvFiles/jira_task_list.csv'"
                    Response: ''
                    - Query: "csv read '../csvFiles/jira_task_list.csv'"
                    Response: ''
                    - Query: "jira tickets '../csvFiles/jira_task_list.csv'"
                    Response: ''

                Be mindful that only the functions defined above are valid, and the response must match the function signature exactly.
                """
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    chain =  RunnablePassthrough.assign(messages=itemgetter("messages")) | prompt | llm 
    with_message_history = RunnableWithMessageHistory(chain, get_session_history, input_messages_key="messages")
    return with_message_history

def updateSessionHistory(session_id: str, message:str):
    if session_id in store:
        get_session_history(session_id).add_message(SystemMessage(message))

def validate_if_function_returned_is_valid(function:str):
    function_name=function.split('(')[0]
    valid_functions=get_valid_functions()
    if function_name in valid_functions:
        return True
    return False

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    with_message_history = connectToLLama()
    while True:
        data = await websocket.receive_text()
        time = datetime.datetime.now().isoformat()
        session_id="001"
        response = with_message_history.invoke(
                {"messages":[HumanMessage(content=data)]},
                config={"configurable": {"session_id": session_id}},
            )
        # add logic to verify if the function returned by LLM is expected
        res = response.content.strip()
        is_valid_function = validate_if_function_returned_is_valid(res)
    
        if len(res)>2 and is_valid_function:
            print(f"is valid{res}")
            # try:
            #     created_jiras = eval(res)
            #     if len(created_jiras)>1:
            #         system_message_for_llm = 'We have created the following jira'
            #         for jiras in created_jiras:
            #             system_message_for_llm = system_message_for_llm + f'\n-${jiras['title']}: https://amagiengg.atlassian.net/browse/${jiras['key']}'
            #         updateSessionHistory(session_id, system_message_for_llm)

            # except Exception as e:
            #     print(f"Error: {e}")

            # await websocket.send_json({
            #     "time":time, "content":res
            # })
        else:
            print("Unexpected response:", res)
        
        