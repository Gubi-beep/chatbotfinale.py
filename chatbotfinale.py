import streamlit as st
from PyPDF2 import PdfReader
import requests
import json
import os

# Ollama API endpoint
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Function to extract text from uploaded PDF
def extract_text_from_pdf(pdf_file):
    pdf_reader = PdfReader(pdf_file)
    extracted_text = ""
    for page_num, page in enumerate(pdf_reader.pages, 1):
        extracted_text += page.extract_text()
    return extracted_text

# Function to save text to a file
def save_text_to_file(text, file_path, append=False):
    mode = "a" if append else "w"
    with open(file_path, mode, encoding="utf-8") as file:
        file.write(text)

# Function to send queries to Ollama
def query_ollama(prompt):
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": "gemma2:2b",  # Adjust the model name based on your Ollama setup
        "prompt": prompt,
    }
    response = requests.post(OLLAMA_API_URL, json=payload, headers=headers)
    if response.status_code == 200:
        try:
            outputs = []
            for line in response.text.splitlines():
                if line.strip():
                    try:
                        json_obj = json.loads(line)
                        outputs.append(json_obj.get("response", ""))
                    except ValueError:
                        continue
            return "".join(outputs).strip() or "No meaningful response received."
        except Exception:
            return "Error processing the response."
    else:
        return f"Error: {response.status_code} - Unable to process the request."

# Streamlit UI setup
st.title("Study Helper Chatbot")

# File paths
SUMMARY_FILE = "summary_and_key_points.txt"
CHAT_HISTORY_FILE = "chat_history.txt"

# File upload section
uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file is not None:
    if "summary_generated" not in st.session_state:
        st.session_state["summary_generated"] = False
        st.session_state["chat_history"] = []

    if not st.session_state["summary_generated"]:
        with st.spinner("Extracting content from PDF..."):
            pdf_text = extract_text_from_pdf(uploaded_file)
            st.success("PDF content extracted successfully!")

            # Save the extracted text to a structured file
            structured_file_path = "extracted_content.txt"
            save_text_to_file(pdf_text, structured_file_path)
            st.success(f"Extracted content saved to {structured_file_path}.")

            # Prepare the initial context for the chatbot
            with open(structured_file_path, "r", encoding="utf-8") as file:
                document_content = file.read()

            st.session_state["document_content"] = document_content

            # Automatically generate a summary and bullet points
            full_prompt = (
                "You are a study assistant chatbot. Generate a detailed summary and key bullet points for the purpose of studying from the provided document content. Make sure it is useful information:\n\n"
                f"{document_content}\n\n"
                "Provide detailed responses without unnecessary elaboration."
            )

            summary_response = query_ollama(full_prompt)

            # Save the summary and bullet points to a file
            save_text_to_file(summary_response, SUMMARY_FILE)
            st.success(f"Summary and key points saved to {SUMMARY_FILE}.")

            # Store the summary in session state
            st.session_state["summary_response"] = summary_response
            st.session_state["summary_generated"] = True

            # Display the summary and bullet points
            st.subheader("Document Summary and Key Points")
            st.text_area("Summary and Key Points:", summary_response, height=300)
    else:
        # Display the saved summary and key points
        st.subheader("Document Summary and Key Points")
        st.text_area(
            "Summary and Key Points:",
            st.session_state["summary_response"],
            height=300,
        )

# Chatbot interaction after the initial response
st.header("Chat with the Study Helper")
user_query = st.text_input("Ask your study-related questions here:")

if user_query:
    with st.spinner("Fetching response..."):
        document_content = st.session_state.get("document_content", "")

        # Prepare the prompt for answering user questions
        question_prompt = (
            "You are a study assistant chatbot. Use the provided document content to answer user queries accurately that can help with studies:\n\n"
            f"{document_content}\n\n"
            f"User's question: {user_query}"
        )

        # Send the prompt to Ollama API and get the response to the user's question
        question_response = query_ollama(question_prompt)

        # Save the chat history (user query + chatbot response) to file
        chat_entry = f"User: {user_query}\nChatbot: {question_response}\n\n"
        save_text_to_file(chat_entry, CHAT_HISTORY_FILE, append=True)

        # Append chat history in session state
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []
        st.session_state["chat_history"].append(chat_entry)

        # Display the chatbot's response
        st.text_area("Chatbot's Response:", question_response, height=200)

# Display chat history
if "chat_history" in st.session_state:
    st.header("Chat History")
    chat_history_display = "".join(st.session_state["chat_history"])
    st.text_area("Chat History:", chat_history_display, height=300)

# Debugging - Display chat history file contents
if st.button("View Chat History File"):
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as file:
            st.text_area("Chat History File Contents:", file.read(), height=300)
    else:
        st.warning("Chat history file not found.")
