from flask import Flask, jsonify, request
import json
import requests
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

@app.route('/api', methods=['POST'])
def post_data():
    # Retrieve JSON data from the request
    data = request.get_json()
    print(data["age"])
    # Process the data or save it to a database
    # For now, let's just return the received data as a response
    response = {
        'status': 'success',
        'data_received': data
    }
    return jsonify(response), 201


@app.route('/api/generate', methods=['POST'])
def get_data():
    data = request.get_json()
    model = "llama3"
    streamResponse = True
    endpoint = "http://localhost:11434"
    systemPrompt = "You are a fast and helpful word predictor, given a sentence with the last word partially completed you should give rest of the letters of the word that would grammatically complete the word in lowercase and no other characters"

    payload = {
        "model": model,
        "prompt": data["input"], 
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

    return jsonify({'data':output}), 200

if __name__ == '__main__':
    app.run(debug=True)