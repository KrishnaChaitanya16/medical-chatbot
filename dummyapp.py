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
text_speech = pyttsx3.init()
app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
load_dotenv()

PINECONE_API_KEY = '784c0e1f-3e6b-435a-841a-2389c2c0c84c'
PINECONE_API_ENV = 'gcp-starter'

embeddings = download_hugging_face_embeddings()

#Initializing the Pinecone
# Set your Pinecone API key
os.environ["PINECONE_API_KEY"] = "784c0e1f-3e6b-435a-841a-2389c2c0c84c"

# Initialize Pinecone
pc = pinecone.Pinecone(api_key="784c0e1f-3e6b-435a-841a-2389c2c0c84c")

index_name = "medical"

#Loading the index
docsearch = Pinecone.from_existing_index(index_name, embeddings)

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
        msg = "Namaste! This is ManasMythri. How may I help you?Is it an emergency ?"
        generate_voice_output(msg)
        session['state'] = 'ask_past_history'
        return "Namaste! This is ManasMythri. How may I help you? Is it an emergency ?"

    elif session['state'] == 'ask_past_history':
        # Process past history and ask for symptoms
        session['past_history'] = input_text
        lowe = input_text.lower()
        if(lowe == 'yes'):
            session['state'] = 'emergency'
            msg = 'Please tell me immediately, the symptoms patient is going through'
            generate_voice_output(msg)
            return "Please tell me immediately, the symptoms patient is going through."
        session['state'] = 'ask_current_symptoms'
        msg = "Please describe your current symptoms."
        generate_voice_output(msg)
        return "Please describe your current symptoms."
    
    elif session['state'] == 'emergency':
        msg = input_text + 'Please give me the immediate guidance.'
        response = qa({"query": msg})
        print(response)  # Print the response object for debugging
        generate_voice_output(response["result"])  # Assuming response["result"] contains the text to be spoken
        session['state'] = 'haha'
        return response["result"]

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
        session['specialists'] = symp + 'For this disease, in one word suggest me the specialists whom I need to consult.'
        response = qa({"query": session['specialists']})
        generate_voice_output(response["result"])
        session['state'] = 'dummy'
        return response["result"]
    
    elif session['state'] == 'dummy':
        session['specialists'] = 'Thank You For Consulting Me. ManasMythri will like to help you always.'
        generate_voice_output(session['specialists'])
        session['state'] = 'haha'
        return session['specialists']
    
    elif session['state'] == 'haha':
        session['haha'] = 'Thankyou. I hope you will recover soon.'
        generate_voice_output(session['haha'])
        session.clear()
        return session['haha']

    return "Invalid state"

def generate_voice_output(text):
    """Generate voice output for the provided text."""
    if text:  # Check if text is not empty or None
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
    else:
        print("No text to speak")


def recommend_medicines(symptoms):
    """Recommend medicines based on symptoms."""
    msg = symptoms + "Suggest few medicines."
    response = qa({"query": msg})
    generate_voice_output(response["result"])
    return response["result"]

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)

