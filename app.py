from flask import Flask, request, jsonify, session
import openai
import os
import requests 

app = Flask(__name__)
app.secret_key = "supersecretkey"
openai.api_key = os.environ.get('OPENAI_API_KEY')

@app.route('/get_objects', methods=['POST'])  # Note the method specification
def user_input():
    incoming_data = request.get_json()  # Get incoming JSON data
    userInput = incoming_data.get('user_input', '') if incoming_data else ''
    if 'history' not in session:
        session['history'] = []
    
    session['history'].append({"role": "user", "content": userInput})
    inputHistory= session['history']  # Using conversation history as prompt

    prompt = ('''You are a shopping assistant with a specific task: to provide improved product recommendations.

After analyzing the user's input, their past requirements, and product recommended last time, your output must strictly adhere to one of the following two formats:

1) A list of 2 to 5 merchandise keywords, without any additional text or explanation, formatted as a list of strings: e.g., ["luxury red leather shoes", "designer red suede shoes", "high-end red patent leather heels"].
  
OR
  
2) An error message that begins with an asterisk '*' followed by a concise error text, only when the input is extremely unclear, offensive, or adversarial.

Try your best to give relevant recommendations based on past and new requirements, and throw and error only when absolutely necessary. Do not include any other types of messages, explanations, or formats.

'''             
        )
    # create a chat completion
    messages_to_send = [{"role": "system", "content": prompt}]
    messages_to_send.extend(session['history'])
    chat_completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=messages_to_send,
    )
    ai_message = chat_completion.choices[0].message.content
    session['history'].append({"role": "assistant", "content": ai_message})
    # Extract and return the chat completion
    return jsonify({"suggested_objects": ai_message})

@app.route('/get_products', methods=['POST'])
def get_products():
    incoming_data = request.get_json()
    user_input = incoming_data.get('user_input', '') if incoming_data else ''

    # Call Node.js API for product search
    node_api_url = "http://localhost:3001/product_search"
    payload = {
        'search_keyword': user_input,
        'number_of_products': 5
    }
    node_response = requests.post(node_api_url, json=payload)
    product_suggestions = node_response.json() if node_response.status_code == 200 else None

    return jsonify({"product_suggestions": product_suggestions})

if __name__ == '__main__':
    app.run(debug=True)