from flask import Flask, request, jsonify, session
import ast
import openai
import os
import requests 
import json
from flask_cors import CORS  # Import the CORS library

app = Flask(__name__)
CORS(app, supports_credentials=True,origins=["https://chat2-cart.vercel.app/"])
app.secret_key = "supersecretkey"
openai.api_key = os.environ.get('OPENAI_API_KEY')

@app.before_request
def before_request():
    if 'history' not in session:
        session['history'] = []

@app.route('/get_objects', methods=['POST'])  # Note the method specification
def user_input():
    try:
        #get user input
        incoming_data = request.get_json()  # Get incoming JSON data
        userInput = incoming_data.get('user_input', '') if incoming_data else ''
        print(userInput)
        if userInput.lower() == "restart history":
            session['history'] = []
            return jsonify({"message": "History restarted", "products": []})
        
        session['history'].append({"role": "user", "content": userInput})

        #get recommendation from gpt3
        prompt1 = ('''You are a shopping assistant with a specific task: to provide improved product recommendations.

    After analyzing the user's input, their past requirements, and product recommended last time, your output must strictly adhere to one of the following two formats:

    1) A list of 1 to 3 merchandise keywords, without any additional text or explanation, formatted as a list of strings: e.g., ["luxury red leather shoes", "designer red suede shoes", "high-end red patent leather heels"].

    OR

    2) An error message that begins with an asterisk '*' followed by a concise error text, only when the input is extremely unclear, offensive, or adversarial.


    Try your best to give relevant recommendations based on past and new requirements and product recommendations, and throw and error only when absolutely necessary. Do not include any other types of messages, explanations, or formats.

    '''             
            )
        
        prompt4 =   '''   
        You are a shopping assistant with a specific task: to provide answers and response to any inquiries regarding products recommended.
        You must return a short answer (max 3 sentences) to any explicid customer questions with an explanation that uses all your knowledge to answer the question about the products recommended.
        Strictly return only the responsein the correct format. Do not include any other types of messages, explanations, or formats.
        '''
        if (userInput[0] == "*"):
            messages_to_send = [{"role": "system", "content": prompt4}]
            messages_to_send.extend(session['history'])
            chat_completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", messages=messages_to_send,
            )
            ai_message = chat_completion.choices[0].message.content
            print(ai_message)
            print("yes1")
            session['history'].append({"role": "assistant", "content": ai_message})
            return jsonify({"message": ai_message,"products": []})
        else:
            messages_to_send = [{"role": "system", "content": prompt1}]
            messages_to_send.extend(session['history'])
            chat_completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", messages=messages_to_send,
            )
            ai_message = chat_completion.choices[0].message.content
            print(ai_message)
            if(ai_message[0] == "*"):
                session['history'].append({"role": "assistant", "content": ai_message})
                return jsonify({"message": ai_message,"products": []})
            session['history'].append({"role": "assistant", "content": ai_message})
            clean_ai_message = ai_message.replace(r"(\w)'(\w)", r"\1\'\2")
            recommendation_list= ast.literal_eval(clean_ai_message)
            
            #get product recommendation from amazon
            amazon_products = get_products(recommendation_list)
            amazon_products_str = json.dumps(amazon_products)
            prompt3 = (f'''Here is a list of amazon product information in json format:

        {amazon_products_str}

        You are a shopping adviser. Based on this information, analyze each product and write a short critical product evaluation for each product. Don't include the title of the product or any links in the evaluation, but discuss the essential features of the product.
        write the evaluations as a Python list of strings. 
        

        ["The HP Pavilion 15 Laptop is equipped with an 11th Gen Intel Core i7-1165G7 Processor, providing good performance for everyday tasks. With 16GB RAM and a 512GB SSD, it offers sufficient storage and fast data access. The full HD IPS micro-edge display enhances visuals, and the 4.3 rating based on 922 reviews indicates its popularity and reliability for general use.", "The HP 15.6 inch Laptop PC is equipped with a 13th Generation Intel Core i7 processor, providing reliable performance. With Intel Iris Xe Graphics, it offers good visuals for multimedia and light gaming. It comes with 16GB DDR4-3200 RAM for smooth multitasking. With a 4.5 rating based on 38 reviews and being labeled as Amazon's Choice, it seems to be a popular and well-received option.", etc.]


        The products must be in the correct order. The output must be in Python with precisely correct syntax. Do not include any other types of messages, explanations, or formats.
        ''')
            
            chat_completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt3}],
            )
            evaluation = chat_completion.choices[0].message.content
            session['history'].append({"role": "assistant", "content": evaluation})
            amazon_products_list = filter_products(amazon_products,ast.literal_eval(evaluation))
            print(amazon_products_list)
                #get reply from gpt3
            prompt2 =(f'''You are a shopping assistant tasked to find the best product based on the customer’s needs. Here is the list of products you can recommend from: \n {amazon_products_str} \nReturn a short message recommending one or two of the product that best fit the customer’s needs. Give only the feature of the product and reason to recommend, DONNOT include any links. Limit the output to less than 50 words. \nUser input: {userInput}''')
            chat_completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt2}],
            )
            reply = chat_completion.choices[0].message.content
            session['history'].append({"role": "assistant", "content": reply})
            session['history'].append({"role": "assistant", "content": str(amazon_products_list)})
            result = {
                'products': amazon_products_list,
                'message': reply,
            }
            session.modified = True
            return jsonify(result)
    except Exception as e:
        print(e)
        return jsonify({"message": "Error occurs. Please enter your needs again", "products": []}), 500  # Added HTTP status code 500

def filter_products(products, descriptions):
    filtered_products = []
    for i, product in enumerate(products):
        filtered_product = {
            "asin": product.get("asin", None),
            "title": product.get("title", None),
            "price": product.get("price", None),
            "url": product.get("url", None),
            "thumbnail": product.get("thumbnail", None),
            "description": descriptions[i] if i < len(descriptions) else None
        }
        filtered_products.append(filtered_product)
    return filtered_products

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