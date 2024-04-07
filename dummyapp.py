from flask import Flask, render_template, request, session
from src.helper import download_hugging_face_embeddings
from langchain_community.vectorstores import Pinecone
import pinecone
from langchain.prompts import PromptTemplate
from langchain_community.llms import CTransformers
from langchain.chains import RetrievalQA
from dotenv import load_dotenv
from src.prompt import prompt_template
import os
import pyttsx3
import gtts
import playsound 
from os.path import exists
import time
import requests  # Add this import statement

text_speech = pyttsx3.init()
app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
load_dotenv()

PINECONE_API_KEY = '784c0e1f-3e6b-435a-841a-2389c2c0c84c'
PINECONE_API_ENV = 'gcp-starter'

embeddings = download_hugging_face_embeddings()

# Initializing the Pinecone
# Set your Pinecone API key
os.environ["PINECONE_API_KEY"] = "784c0e1f-3e6b-435a-841a-2389c2c0c84c"

# Initialize Pinecone
pc = pinecone.Pinecone(api_key="784c0e1f-3e6b-435a-841a-2389c2c0c84c")

index_name = "medical"

# Loading the index
docsearch = Pinecone.from_existing_index(index_name, embeddings)

# Define the prompt template


PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])

chain_type_kwargs = {"prompt": PROMPT}

llm = CTransformers(model="llama-2-7b-chat.ggmlv3.q4_0.bin",
                    model_type="llama",
                    config={'max_new_tokens':2048,
                            'temperature':0.8,'context_length': 10000})

qa = RetrievalQA.from_chain_type(
    llm=llm, 
    chain_type="stuff", 
    retriever=docsearch.as_retriever(search_kwargs={'k': 2}),
    return_source_documents=True, 
    chain_type_kwargs=chain_type_kwargs)

symp = ' '

# Mappls API key
MAPPLS_API_KEY = '7cd126cb40ffcdf277dd8d66859f57b1'

# Mappls API endpoint for specialist search
MAPPLS_API_ENDPOINT = 'https://api.mapps.com/v4/search/by-category'

@app.route("/")
def index():
    session.clear()  # Clear session data
    return render_template('dummy.html')

@app.route("/get", methods=["POST"])
def chat():
    global j
    global symp
    msg = request.form["msg"]
    input_text = msg

    if 'state' not in session:
        # Introduction message
        j = 0
        msg = "Namaste! This is ManasMythri. How may I help you?"
        generate_voice_output(msg)
        session['state'] = 'ask_past_history'
        return "Namaste! This is ManasMythri. How may I help you?"

    elif session['state'] == 'ask_past_history':
        # Process past history and ask for symptoms
        session['past_history'] = input_text
        session['state'] = 'ask_current_symptoms'
        msg = "Please describe your current symptoms."
        generate_voice_output(msg)
        return "Please describe your current symptoms."

    elif session['state'] == 'ask_current_symptoms':
        # Process symptoms and get answer
        session['current_symptoms'] = input_text
        response = qa({"query": session['current_symptoms']})
        symp = response["result"]
        generate_voice_output(response["result"])
        session['state'] = 'suggest_medicines' 
        
        return response["result"]
    
    elif session['state'] == 'suggest_medicines':
        # Recommend medicines based on symptoms
        session['suggest_medicines'] = input_text
        response = qa({"query": session['suggest_medicines']})
        generate_voice_output(response["result"])
        session['state'] = 'specialists'
        
        return response["result"]
    
    elif session['state'] == 'specialists':
        session['specialists'] = symp + ' For this disease, in one word suggest me the specialists whom I need to consult.'
        generate_voice_output(session['specialists'])
        
        # Get the specialist type from session data
        specialist_type = session.get('specialist_name', '')
        
        if specialist_type:
            # Call find_specialists function to get specialist information
            location = "Bengaluru, India"  # Or provide latitude/longitude as a dictionary
            specialists = find_specialists(location, specialist_type)
            
            if specialists:
                # Format specialist information as a response
                response = "\n".join([f"{specialist['name']}, Rating: {specialist['rating']}, Address: {specialist['address']}" for specialist in specialists])
            else:
                response = "No specialists found in the area."
            
            session['state'] = 'dummy'
            return response
        else:
            session['state'] = 'dummy'
            return "No specialist type found in session data."
    
    elif session['state'] == 'dummy':
        session['specialists'] = 'Thank You For Consulting Me. ManasMythri will like to help you always.'
        generate_voice_output(session['specialists'])
        session['state'] = 'haha'
        return session['specialists']
    
    return "Invalid state"

def generate_voice_output(text):
    """Generate voice output for the provided text."""
    sound = gtts.gTTS(text, lang="en")
    
    file_exists = exists("response1.mp3")

    if not file_exists:
        sound.save("response1.mp3")
    else:
        sound.save("response2.mp3")
    
    # Play audio file asynchronously
    if not file_exists:
        playsound.playsound("response1.mp3", block=False)
    else:
        playsound.playsound("response2.mp3", block=False)
    
    time.sleep(1)
    # Delete audio file
    if not file_exists:
        os.remove('response1.mp3')
    else:
        os.remove('response2.mp3')
    
    return

def find_specialists(location, specialist_type):
    """
    Fetches specialist information near the user's location using Mappls API.

    Args:
        location (str): User's location (city, zip code, address).
        specialist_type (str): Type of specialist to search for.

    Returns:
        list: A list of dictionaries containing details of the top 3 specialists,
              or an empty list if no specialists are found.

    Raises:
        requests.exceptions.RequestException: If an error occurs during the API request.
    """

    params = {
        "apiKey": MAPPLS_API_KEY,
        "category": specialist_type
    }

    # Geocoding API endpoint to convert location to coordinates (optional)
    if not isinstance(location, dict):
        geocode_url = f"https://api.mapps.com/v4/geocode/forward?apiKey={MAPPLS_API_KEY}&query={location}"
        geocode_response = requests.get(geocode_url)
        geocode_response.raise_for_status()  # Raise exception for non-200 status codes

        location_data = geocode_response.json()
        latitude = location_data["latitude"]
        longitude = location_data["longitude"]

        # Update params with coordinates if geocoding is successful
        params.update({"latitude": latitude, "longitude": longitude})

    try:
        response = requests.get(MAPPLS_API_ENDPOINT, params=params)
        response.raise_for_status()  # Raise exception for non-200 status codes

        search_data = response.json()
        top_three_specialists = []

        # Process search data to extract top 3 specialists (refer to Mappls docs)
        for place in search_data["places"][:3]:
            name = place.get("name", "NA")
            rating = place.get("rating", "NA")
            address = place.get("address", "NA")
            top_three_specialists.append({"name": name, "rating": rating, "address": address})

        return top_three_specialists

    except requests.exceptions.RequestException as e:
        print(f"Error fetching specialists from Mappls API: {e}")
        return []  # Return empty list on error

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
