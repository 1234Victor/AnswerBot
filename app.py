from flask import Flask, request, jsonify
import ast
import openai
import os
import requests 
import json
from flask_cors import CORS  # Import the CORS library

app = Flask(__name__)
CORS(app) 
app.secret_key = "supersecretkey"
#openai.api_key = os.environ.get('OPENAI_API_KEY')
openai.api_key = "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"
history = []
@app.route('/get_objects', methods=['POST'])  # Note the method specification
def user_input():
    global history
    #get user input
    incoming_data = request.get_json()  # Get incoming JSON data
    userInput = incoming_data.get('user_input', '') if incoming_data else ''
    try:
        if userInput.lower() == "restart history":
            history = []
            return jsonify({"message": "History restarted"})
        
        history.append({"role": "user", "content": userInput})

        #get recommendation from gpt3
        prompt1 = ('''You are a shopping assistant with a specific task: to provide improved product recommendations.

    After analyzing the user's input, their past requirements, and product recommended last time, your output must strictly adhere to one of the following three formats:

    1) A list of 1 to 3 merchandise keywords, without any additional text or explanation, formatted as a list of strings: e.g., ["luxury red leather shoes", "designer red suede shoes", "high-end red patent leather heels"].
    
    OR

    2) Answer to any explicid customer questions that begins with an asterisk '*' followed by an explanation that uses all your knowledge to answer the question about the products recommended.

    OR
    
    3) An error message that begins with an asterisk '*' followed by a concise error text, only when the input is extremely unclear, offensive, or adversarial.


    Try your best to give relevant recommendations based on past and new requirements and product recommendations. Return an answer only to explicit questions about products recommended, and throw and error only when absolutely necessary. Do not include any other types of messages, explanations, or formats.

    '''             
            )
    
        messages_to_send = [{"role": "system", "content": prompt1}]
        messages_to_send.extend(history)
        chat_completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=messages_to_send,
        )
        ai_message = chat_completion.choices[0].message.content
        if(ai_message[0] == "*"):
            history.append({"role": "assistant", "content": ai_message})
            return jsonify({"message": ai_message})
        history.append({"role": "assistant", "content": ai_message})
        clean_ai_message = ai_message.replace(r"(\w)'(\w)", r"\1\'\2")
        recommendation_list= ast.literal_eval(clean_ai_message)
        
        #get reply from gpt3
        prompt2 =(f'''You are a shopping assistant tasked to find the best product based on the customer’s needs. Here is the list of products you can recommend from: \n {ai_message} \nReturn a short message recommending one or two of the product that best fit the customer’s needs. Give only the name of the product and reason for recommendation. Limit the output to less than 100 words. \nUser input: {userInput}''')
        chat_completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt2}],
        )
        reply = chat_completion.choices[0].message.content
        
        #get product recommendation from amazon
        amazon_products = get_products(recommendation_list)
        amazon_products_str = json.dumps(amazon_products)
        prompt3 = (f'''Here is a list of amazon product information in json format:

    {amazon_products_str}

    You are a shopping adviser. Based on this information, analyze each product and write a short product evaluation for each product.
    Add the evaluation as a string ("ai_description"). You must put it in the format shown in the following example (return ai_description, thumbnail, title, and url for each product).

    [{{}}
        {{
            "ai_description": "The ASUS VivoBook S15 S533 Thin and Light Laptop offers a 15.6-inch FHD display, Intel Core i7-1165G7 CPU, 16GB DDR4 RAM, and a 512GB PCIe SSD. It has a rating of 4.4 out of 5 stars with 133 reviews. The laptop is not currently discounted or on sale. It is not sponsored, an Amazon Choice, a best seller, or eligible for Amazon Prime.",
            "thumbnail": "https://m.media-amazon.com/images/I/71oRxpP3T0L._AC_UY218_.jpg",
            "title": "ASUS VivoBook S15 S533 Thin and Light Laptop, 15.6” FHD Display, Intel Core i7-1165G7 CPU, 16GB DDR4 RAM, 512GB PCIe SSD, ...",
            "url": "https://www.amazon.com/ASUS-VivoBook-i7-1165G7-Fingerprint-S533EA-DH74-WH/dp/B08KH4RVBM/ref=sr_1_1?keywords=i7+white+laptop&qid=1693106164&sr=8-1"
        }},
        {{
            "ai_description": "The ASUS TUF Dash 15 (2021) Ultra Slim Gaming Laptop features a 15.6-inch 240Hz FHD display, GeForce RTX 3070, Intel Core i7-11375H, 16GB DDR4 RAM, and a 1TB SSD. It has a rating of 4.4 out of 5 stars with 49 reviews. The laptop is currently discounted, with a before-discount price of $1,499.99. It is not sponsored, an Amazon Choice, a best seller, or eligible for Amazon Prime.",
            "thumbnail": "https://m.media-amazon.com/images/I/81xPTxloCtL._AC_UY218_.jpg",
            "title": "ASUS TUF Dash 15 (2021) Ultra Slim Gaming Laptop, 15.6 240Hz FHD, GeForce RTX 3070, Intel Core i7-11375H, 16GB DDR4, 1T...",
            "url": "https://www.amazon.com/ASUS-TUF516PR-DS77-WH-i7-11375H-Windows-Notebook/dp/B099QXCBKN/ref=sr_1_2?keywords=i7+white+laptop&qid=1693106164&sr=8-2"
        }}
    ]

    Return only the above json file. Do not include any other types of messages, explanations, or formats.
    ''')

        chat_completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt3}],
        )
        evaluation = chat_completion.choices[0].message.content
        history.append({"role": "assistant", "content": evaluation})
        
        print(recommendation_list)
        print(reply)
        print(history)
        return json.loads(evaluation)
    except Exception as e:
        print(e)
        return jsonify({"message": "Something went wrong"})


def get_products(user_input):

    # Call Node.js API for product search
    node_api_url = "https://amazonbot123.onrender.com/product_search"
    payload = {
        'search_keyword': user_input,
        'number_of_products': 3
    }
    node_response = requests.post(node_api_url, json=payload)
    product_suggestions = node_response.json() if node_response.status_code == 200 else None

    return product_suggestions
if __name__ == '__main__':
    app.run(debug=True)