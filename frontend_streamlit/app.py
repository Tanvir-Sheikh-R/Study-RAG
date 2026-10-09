import streamlit as st
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

with open(PROJECT_ROOT / "chapters.json", "r", encoding="utf-8") as file:
    INDEX_INFOS: dict = json.load(file)


st.title('বই বন্ধু')

class_name_dict = {"5": "৫ম শ্রেণী", "6": "৬ষ্ঠ শ্রেণী", "7": "৭ম শ্রেণী", "8": "৮ম শ্রেণী", "9": "৯ম শ্রেণী", "10": "১০ম শ্রেণী"}
converted_class_name = [class_name_dict[key] for key in INDEX_INFOS.keys()]

with st.sidebar:
    st.header("Search by Chapter")
    class_number = st.selectbox("Select your Class:", ["___"] + converted_class_name)

    if class_number == "___":
        st.info("Please select a class from the sidebar to view data.")
        st.stop()

    CLASS_KEY = [key for key, value in class_name_dict.items() if value == class_number][0]

    SUM_NAME = st.selectbox("Select your Subject:", ["___"] + list(INDEX_INFOS[CLASS_KEY].keys()))

    if SUM_NAME == "___":
        st.info("Please select a subject from the sidebar to view data.")
        st.stop()

    chap = list(INDEX_INFOS[CLASS_KEY][SUM_NAME])

    CHAPTER_NAME = st.selectbox("Select your Chapter:", chap)
    st.divider()
    st.button("শুরু করি", type="primary", use_container_width=True)


# ************************** Chat Section ***********************


# 1. Initialize chat history in session state if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. Display all previous messages from history on rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. Accept new user input
if prompt := st.chat_input("Ask a question about your books..."):

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Generate an assistant response
    response = f"Echoing back your query for class context: {prompt}"

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(response)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
