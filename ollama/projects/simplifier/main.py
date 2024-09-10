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
import requests
from io import StringIO
import re

load_dotenv()

model="llama3.1"
llm = ChatOllama(model=model, temperature=0)

app = FastAPI()

# @app.get("/")
# async def root():
#     return {"message": "asdf     World"}

# @app.get("/")
# async def get():
#     return HTMLResponse(html)

#TODO: should login to jira on application start, if session ends should re-login

try:
    jira = Jira(
    url=os.getenv("url"),
    username=os.getenv("username"),
    password=os.getenv("password"),
    cloud=True)
except Exception as e:
    print(f"Unable to login to jira, Error: {e}")

def create_jira(fields, row):
    try:
        # jira_issue_response will contain {'id': '2784859', 'key': 'AN30-6067', 'self': 'link to the json response'}
        jira_issue_response=jira.issue_create(fields)
        updated_jira_issue_response=jira_issue_response
        updated_jira_issue_response['title']=row['summary']
        print('in create_jira', updated_jira_issue_response)
        return {
            "error": False,
            "message": '',
            "content": updated_jira_issue_response
        }
    except Exception as e:
        print(f'Failed to create the jira {row['summary']} - {e}')
        return {
            "error": True,
            "message": f'Failed to create the jira for {row['summary']} - {e}\nWe will stop trying to create further jira as chance of failure is high,\nPlease check with admin for more details',
            "content": ''
        }

def process_google_sheet_endpoint(endpoint: str):
    print(endpoint)
    #Can you read the csv from https://docs.google.com/spreadsheets/d/1mPO6-Ta-3t3ECROxzebG9DwiDe7Ran5/edit?gid=0#gid=0 and create jira for each items
    google_sheet_endpoint_pattern = r"https://docs.google.com/spreadsheets/d/([a-zA-Z0-9-_]+).*?gid=([0-9]+)"
    match = re.search(google_sheet_endpoint_pattern, endpoint)

    if match:
        sheet_id = match.group(1)
        gid = match.group(2)
        if gid:
            return {
                "error": False,
                "message": '',
                "content": f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?gid={gid}&format=csv'
            }
        return {
                "error": False,
                "message": '',
                "content": f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv'
            }
        
    else:
        print("URL format is not recognized.")
        return {
            "error": True,
            "message": f'URL format is not recognized. - {endpoint}',
            "content": ''
        }

def create_jira_task_from_endpoint(endpoint:str):
    processed_end_point = process_google_sheet_endpoint(endpoint)
    created_jira = []
    
    if processed_end_point['error']:
        return processed_end_point
    
    print('in create_jira-task_from_endpoint, processed_end_point', processed_end_point)
    try:
        response = requests.get(processed_end_point['content'])
    except Exception as e:
        print(f'Failed to access the endpoint - {e}')
        return {
            "error": True,
            "message": f'Failed to access the endpoint - {e}',
            "content": ''
        }
    csv_data = StringIO(response.content.decode('utf-8'))
    df = pd.read_csv(csv_data)
    
    print('in create_jira-task_from_endpoint', df)
    
    if df.empty:
        print(f'Empty data frame\nPlease check if the URL is correct and it has data in supported format. Received URL: {endpoint}')
        return {
            "error": True,
            "message": f'Empty data frame\nPlease check if the URL is correct and it has data in supported format. Received URL: {endpoint}',
            "content": ''
        }
    

    #TODO: add validation to check if summary column is present or not, if not present update the ws message
    

    for index, row in df.iterrows():
        fields = {'project':{'key':'AN30'},'issuetype': {'name': 'Task'},'summary': row['summary'], 'description':row['description'], 'assignee':{'id':row['assignee']}}
        try:
            print('inside try of create_jira_task_from_endpoint')
            if pd.notna(row['summary']) and pd.isna(row['jira']):
                print('inside try if of create_jira_task_from_endpoint')
                jira_response = create_jira(fields,row)
                print('inside try if of create_jira_task_from_endpoint - jira_response', jira_response)
                if jira_response['error']:
                    return jira_response
                    
                created_jira.append(jira_response['content'])

                # the below line of code will update the data frame for column jira
                df.at[index, 'jira'] = f'https://amagiengg.atlassian.net/browse/{jira_response['key']}'
            elif pd.notna(row['jira']):
                print(f'inside try elif of create_jira_task_from_endpoint, skipping row, jira is present. ${pd(row['jira'])}')
            else:
                #TODO: summary column present but no data
                print('summary not present')
                
        except Exception as e:
            print('inside except of create_jira_task_from_endpoint')
            return {
                "error": True,
                "message": e,
                "content": ''
            }
            
    print('in create_jira_task_from_endpoint', created_jira)
    return {
            "error": False,
            "message": '',
            "content": created_jira
        }

store = {}

def get_valid_functions():
    return ['create_jira_task_from_local_CSV_file','create_jira_task_from_endpoint']

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
                    - create_jira_task_from_endpoint(endpoint)

                Constraints:
                    - Only use the functions listed above. Do not generate or suggest any other functions.
                    - Ensure that the function you generate directly addresses the query made by the user.
                    - If the query does not correspond to any function you are allowed to use, respond with an empty string ''.
                    - Include only the function name and arguments in your response, without any additional text.
                    - If there is no path mentioned in the query then respond with empty string ''.
                    - If the question is related to any task we did in the current session then you should give relevant answer.
                    - When the query is asking to create jira tickets then it should also have a https URL otherwise respond with empty string ''.
                    - While responding replace [URL] with the actual URL provided by the user

                Examples:
                    - Query: "Can you read the csv from [URL] and create jira for each items" 
                    Response: "create_jira_task_from_endpoint('[URL]')"
                    - Query: "read the csv in the path [URL] and create jira for each items" 
                    Response: "create_jira_task_from_endpoint('[URL]')"
                    - Query: "csv read jira [URL]"
                    Response: ''
                    - Query: "csv read [URL]"
                    Response: ''
                    - Query: "jira tickets [URL]"
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
        res = response.content.strip()
        print(f'Response from LLM - {res}')
        is_valid_function = validate_if_function_returned_is_valid(res)
    
        if len(res)>2 and is_valid_function:
            try:
                response_from_function_execution = eval(res)
                if response_from_function_execution['error']:
                    await websocket.send_json({
                        "time":time, "content":response_from_function_execution['message']
                    })
                    return
                
                print('created_jira', response_from_function_execution['content'])
                if len(response_from_function_execution['content'])>=1:
                    system_message_for_llm = 'We have created following jira'
                    for jira in response_from_function_execution['content']:
                        system_message_for_llm = system_message_for_llm + f'\n-{jira['title']}: https://amagiengg.atlassian.net/browse/{jira['key']}'
                    updateSessionHistory(session_id, system_message_for_llm)
                    await websocket.send_json({
                        "time":time, "content":system_message_for_llm
                    })

            except Exception as e:
                print(f"Error: {e}")
                await websocket.send_json({
                    "time":time, "content":f'Failed to execute the function: {res}\nPlease contact the admin'
                })
                
        elif len(res)<=2:
            print("Unexpected response:", res)
            # TODO: update error message with the supported features
            await websocket.send_json({
                "time":time, "content":f'Unexpected response from LLM: {res}\nPlease double check your query'
            })
                
        else:
            print(res)
            # TODO: update error message with the supported features
            await websocket.send_json({
                "time":time, "content":f'{res}'
            })
        
        