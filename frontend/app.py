import streamlit as st
import json
from pathlib import Path
# from pipeline.settings.config import Config

PROJECT_ROOT = Path(__file__).resolve().parent.parent

with open(PROJECT_ROOT / "chapters.json" , "r", encoding="utf-8") as file:
    INDEX_INFOS : dict = json.load(file)


st.title('বই বন্ধু')

class_name_dict = {"class_5": "৫ম শ্রেণী", "class_6": "৬ষ্ঠ শ্রেণী", "class_7": "৭ম শ্রেণী", "class_8": "৮ম শ্রেণী", "class_9_10": "৯ম-১০ম শ্রেণী"}
converted_class_name = map(lambda x: class_name_dict[x], INDEX_INFOS['all_books'].keys())

with st.sidebar:
    st.header("Search by Chapter")
    class_number = st.selectbox("Select your Class:", ["___"] + list(converted_class_name))

    if class_number == "___":
        st.info("Please select a class from the sidebar to view data.")
        st.stop()

    CLASS_NUMBER = [key for key, value in class_name_dict.items() if value == class_number]


    SUM_NAME = st.selectbox("Select your Subject:", ["___"] + list(INDEX_INFOS['all_books'][CLASS_NUMBER[0]].keys()))

    if SUM_NAME == "___":
        st.info("Please select a subject from the sidebar to view data.")
        st.stop()
    
    # sub_name = [key for key, value in INDEX_INFOS['all_books'][class_number[0]].items() if value == sub_name]

    chap = [name["chapter_name"] for name in INDEX_INFOS['all_books'][CLASS_NUMBER[0]][SUM_NAME]]

    CHAPTER_NAME = st.selectbox("Select your Chapter:", chap)
    st.divider()
    st.button("শুরু করি", type="primary", width="stretch")




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




