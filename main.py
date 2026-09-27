import pytesseract
from pdf2image import convert_from_path
from PIL import ImageOps
import os
from tqdm import tqdm
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_deepseek import ChatDeepSeek
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



pdf_path = r"pdf\Class 10\Secondary (BV)-2026_Class 9-10_Career_compressed.pdf"
poppler_path = r"C:\poppler\Library\bin"  # adjust to your install
output_dir = "extracted_text"
os.makedirs(output_dir, exist_ok=True)

# Convert all pages to images


text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1300,
        chunk_overlap=300,
        length_function=len,
        is_separator_regex=False,
        separators=["\n\n", "\n", "।", " ", ""],
    )



def pdf_to_text_file(pdf_path):

    pages = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_path)

    full_text = []
    for i, page in enumerate(tqdm(pages, desc="OCR Processing...")):
        # Preprocess: grayscale + contrast boost (helps Bangla conjuncts a lot)
        img = page.convert('L')
        img = ImageOps.autocontrast(img)

        text = pytesseract.image_to_string(img, lang='ben')
        full_text.append(f"[PAGE_{i-4}]\n{text}")

        print(f"--- Page {i+1}/{len(pages)} done ---")

    # Save as one combined text file
    with open(os.path.join(output_dir, f"{pdf_path[13:-4]}_book_full.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(full_text))

    print("Done. Saved to", os.path.join(output_dir, "book_full.txt"))



def text_to_chunks(pdf_path):
    with open(os.path.join(output_dir, pdf_path), "r", encoding="utf-8") as f:
        text = f.read()
    chunks  = text_splitter.create_documents([text])
    return chunks 



documents = text_to_chunks("book_full.txt")


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