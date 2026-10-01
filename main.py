import pytesseract
from pdf2image import convert_from_path
from PIL import ImageOps
import os
from tqdm import tqdm

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_deepseek import ChatDeepSeek
from pipeline.pdf_to_document import build_documents
import os


load_dotenv()

llm = ChatOpenAI(
    model="nvidia/nemotron-3.5-lightning:free",  # any OpenRouter model slug
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),

    max_completion_tokens=2048
)

llm_groq = ChatGroq(
    model = 'openai/gpt-oss-20b',
    max_tokens=1024
)


llm_deep = ChatDeepSeek(
    model="deepseek-flash",
    temperature=0.5,
    max_tokens=1024
)



embeddings = HuggingFaceEmbeddings(
    model_name="intfloat/multilingual-e5-large",
    cache_folder="./model_cache" 
    )




# Convert all pages to images



persist_directory = "./bangla_book_db"

if os.path.exists(persist_directory) and os.listdir(persist_directory):
    # DB already built — just load it, don't re-embed
    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings,
        collection_name="nctb_book"
    )
    print("Loaded existing vectorstore.")
else:
    # First run — build and persist
    documents = build_documents()
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_directory,
        collection_name="nctb_book"
    )
    print("Built new vectorstore.")


retriver = vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": 6, "lambda_mult": 0.25})


query = "নিরুপমা তার স্বপ্পনপূরণের পথটি কিভাবে দেখতে পান?"

result = retriver.invoke(query)


prompt = PromptTemplate.from_template(
    """You are a Bangla teacher, an expert in many subjects.
        From the given query: {query}
        With the provided content read carefully: {content} 
        Give the answer only in the Bangla language."""
)

final_prompt = prompt.invoke({'query': query, 'content':result})

output = llm_deep.invoke(final_prompt)

print(output.content)