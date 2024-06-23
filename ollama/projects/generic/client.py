import json
import requests

model = "llama3"
streamResponse = True
endpoint = "http://localhost:11434"
systemPrompt = "You are a fast and helpful word predictor, given a sentence with the last word partially completed you should give rest of the letters of the word that would grammatically complete the word in lowercase and no other characters"

def generate(prompt):
    payload = {
        "model": model,
        "prompt": prompt, 
        "system": systemPrompt,
        "stream": streamResponse
    }
    payload_json = json.dumps(payload)
    headers = {"Content-Type": "application/json"}
    response = requests.post(endpoint+"/api/generate", data=payload_json, headers=headers, stream=streamResponse)
    response.raise_for_status()
    output = "" 
    for line in response.iter_lines():
        body = json.loads(line)
        if "error" in body:
            raise Exception(body["error"])
        if body.get("done") is False:
            message = body.get("response", "")
            output += message
            # the response streams one token at a time, print that as we receive it
            print(message, end="", flush=True)
        if body.get("done") is True:
            message = body.get("response", "")
            print(message)
    


def chat(messages):
    r = requests.post(
        endpoint+"/api/chat",
        json={"model": model, "messages": messages, "stream": streamResponse},
    stream=streamResponse
    )
    r.raise_for_status()
    output = ""

    for line in r.iter_lines():
        body = json.loads(line)
        if "error" in body:
            raise Exception(body["error"])
        if body.get("done") is False:
            message = body.get("message", "")
            content = message.get("content", "")
            output += content
            # the response streams one token at a time, print that as we receive it
            print(content, end="", flush=True)

        if body.get("done") is True:
            message = body.get("message", "")
            content = message.get("content", "")
            print(content)

def initialiseChat():
    messages = []

    while True:
        user_input = input("Enter a prompt: ")
        if not user_input:
            exit()
        print()
        messages.append({"role": "user", "content": user_input})
        chat(messages)
        print("\n\n")

def initialiseGenerate():
    while True:
        user_input = input("Enter a prompt: ")
        if not user_input:
            exit()
        print()
        generate(user_input)
        print('\n\n')

def initialisePrompt():
    userInput = input("What do you want to do? \n 1.Chat \n 2.Analyze a document\n\n")

    if userInput != "1" and userInput != "2":
        print("Supported values are 1 and 2")
        initialisePrompt()
    elif userInput == "1":
        initialiseChat()
    elif userInput == "2":
        initialiseGenerate()

def main():
    initialisePrompt()

if __name__ == "__main__":
    main()