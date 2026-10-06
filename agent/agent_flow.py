from langchain_groq import ChatGroq
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import Tool
from langchain_core.prompts import PromptTemplate

from dotenv import load_dotenv
import os
from langgraph.graph import StateGraph, START, END

load_dotenv()

llm_deepseek = ChatDeepSeek(model="deepseek-chat", temperature=1, max_tokens=10000)
llm_groq = ChatGroq(model="openai/gpt-oss-120b", temperature=1, max_tokens=10000)


SYSTEM_PROMPT = """You are an expert Bengali tutor. Answer the user's question accurately using the provided context.
If the answer is not in the context, say so.
Respond in Bengali."""

prompt = PromptTemplate(input_variables=["context", "question"], template="""
                        Here is the context:
                        {context}

                        Now answer this question:
                        {question}
                        
                        Remember to answer in Bengali and strictly within the bounds of the context provided.
                    """)


def chat_agent():
    chat = prompt | llm_groq


# from laya import LayaClient # Typical local or API client wrapper

# # Ensure you call the router or pass the language hint
# client = LayaClient(model="laya-multilingual")

# from laya import Router

# router = Router(preload=True)  # load once, reuse across chunks

# QUESTIONS = {
#     "relevance": {
#         "type": "choice",
#         "options": ["answers_question", "partial_context", "noise"],
#     }
# }

# def evaluate_bangla_chunk(user_query: str, bangla_chunk: str):
#     state = f"প্রশ্ন: {user_query}\nটুকরো: {bangla_chunk}"
#     return router.predict(state, QUESTIONS, lang_guess="bn")

# user_query = "ঢাকা মেট্রোরেলের এমআরটি লাইন-৬ এর মোট দৈর্ঘ্য কত কিলোমিটার?"
# bangla_chunk = "ঢাকা মেট্রোরেলের এমআরটি লাইন-৬ উত্তরা উত্তর থেকে মতিঝিল পর্যন্ত নিয়মিত যাত্রী পরিবহন করছে। প্রতিদিন হাজার হাজার যাত্রী এই রুটে যাতায়াত করেন এবং এটি যানজট কমাতে বড় ভূমিকা রাখছে।"

# answer = evaluate_bangla_chunk(user_query, bangla_chunk)

# print(answer)



import requests
from langchain_core.documents import Document

# 1. Chunks retrieved from your vector store
chunks = [Document(id='91b10203-e079-422d-9b10-0df4176d7570', metadata={'class_number': 'class_6', 'book_name': 'bgs', 'chapter': 'সমাজ বিবর্তনের ইতিহাস', 'page_end': 9, 'page_start': 1}, page_content='passage: কাজ-: বাংলাদেশের সমাজ যেন মানব সমাজ বিকাশের স্তরসমূহের ধারাবাহিক ফসল"-বিশ্লেষণ করো\nঅনুশীলনী\nবহুনির্বাচনি প্রশ্ন ১ শীতল পাটির জন্য বিখ্যাত অঞ্চল কোনটি? ক রাজশাহী খ খুলনা গ. ফরিদপুর ঘ সিলেট ১ নারীই প্রথম কৃষি কাজ শুরু করেন, কারণ তাদের ছিল - |. সৃজনশীল দৃষ্টিভঙ্গি 11. খাবার সংগ্রহের দায়িত্ব পালন I11. দায়িত্বপালনের বাধ্যবাধকতা নিচের কোনটি সঠিক? ক 4 খ i ও ii\n?\nগ ||1\nঘ. \', 11 ও iii'),
                    Document(id='e8f044ff-07fa-46a5-8e55-15ecf4169914', metadata={'chapter': 'বাংলাদেশের ইতিহাস', 'class_number': 'class_6', 'page_end': 18, 'book_name': 'bgs', 'page_start': 10}, page_content="passage: সৃজনশীল প্রশ্ন\nপ্রচুর ধান উতপাদন আকাশপথে আমেরিকায় তৈরি পোশাক রপ্তানি / বিভিন্ন ধরনের দেশীয় ফল উতপাদন পাটজাত দ্রব্য বিশ্বব্যাপী প্রশংসিত তথ্য -১ তথ্য - $ ক মাৎস্যন্যায় কী? খ বাংলা কীভাবে একটি প্রদেশে পরিণত হয়? গ. তথ্য-১ এর মতো প্রাচীন বাংলাদেশের গৌরবময় ক্ষেত্রটি ব্যাখ্যা করো চা তথ্য-২ এ উল্লিখিত বিষয়গুলো প্রাচীন বাংলাদেশের গৌরবের সাথে সাদৃশ্যপূর্ণ মতামত দাও সংক্ষিপ্ত-উত্তর প্রশ্ন ১. শিক্ষার ক্ষেত্রে কীভাবে প্াচীন বাংলার মানুষ এগিয়ে ছিল? $ সুলতানি আমলে বাংলার স্থাপত্যশিল্পের দুটি নিদর্শনের বর্ণনা দাও ৩. ১৬ই ডিসেম্বর বাংলাদেশের ইতিহাসে গুরুত্বপূর্ণ কেন? 8. জুলাই গণঅভ্যুত্থানকে ঐক্য এবং সাহসের উজ্জ্বল দৃষ্টান্ত' বলা হয় কেন?\n?"),
                    Document(id='ea9fca14-db6a-434f-86f6-69db360bec75', metadata={'page_end': 55, 'book_name': 'bgs', 'class_number': 'class_6', 'chapter': 'শিশুর বেড়ে ওঠা ও প্রতিবন্ধকতা: সামাজিকীকরণ', 'page_start': 49}, page_content='passage: ৫8\nবাংলাদেশ ও বিশপরিচয়\nভালো পরিবেশে শিশুরা বেড়ে উঠলে পরিবার ও সমাজের প্রতি তারা   দায়িত্বশীল হয়ে উঠবে এসব শিশুর প্রতি ভালো আচরণের মাধ্যমে আমরা নিজেরাও মানবিক গুণসম্পন্ন একজন নাগরিক হয়ে উঠব আমরা পরিবারের অন্যান্যদেরও তাদের প্রতি ভালো আচরণ করার জন্য বলব /\nকাজ বাড়ির কাজে সহায়তাকারীর প্রতি আমাদের আচরণ কেমন হওয়া উচিত?\nঅনুশীলনী\nবহুনির্বাচনি প্রশ্ন ১ শিশুর সামাজিকীকরণ শুরু হয় কোনটি থেকে? ক খেলার সাথি খ প্রতিবেশী গ. পরিবার সা শিক্ষা প্রতিষ্ঠান\n১ শিশুশমের কারণ- 4* শিশুদের অবাধ্যতা 11. পারিবারিক আর্থিক সংকট\nii1. পারিবারিক অশান্তি\nনিচের কোনটি সঠিক? ক i ও 11\nখ. 1i ও 1ii\nগ  ও iii\nঘ 1, ii ও iii\nনিচের উদ্দীপকটি পড়ে ৩ ও ৪ নম্বর প্রশ্নের উত্তর দাও | বন্ধুদের সাথে বেড়াতে গিয়ে মাহিন পথ হারিয়ে ফেলে পথ চিনিয়ে দেওয়ার কথা বলে এক লোক তাকে পার্শ্ববর্তী দেশের কিছু অপরিচিত লোকের হাতে তুলে দেয় সেখানে মাহিনকে জোরপূর্বক ওয়েল্ডিং মেশিনের কাজে নিয়োজিত করে মাহিনকে হারিয়ে ছোটো ছেলে জাহিদকে বাবা-মা লেখাপড়া , আবৃত্তি , গান ইত্যাদি সকল ক্ষেত্রেই যোগ্য করে তোলার জন্য অতিরিক্ত চাপ দেন'),
                    Document(id='8b350887-63d5-41d4-8f77-89147d312d19', metadata={'page_start': 1, 'page_end': 9, 'book_name': 'bgs', 'class_number': 'class_6', 'chapter': 'সমাজ বিবর্তনের ইতিহাস'}, page_content='passage: 8\nবাংলাদেশ ও বিশপরিচয়\nও কন্দ আস্তানার আশপাশে গম ও বালির যেসব দানা পড়ত তা থেকে গজিয়ে উঠত চারা গাছ চারা গাছে পরে দেখা দিত শিষ ও দানা এ ধরনের ঘটনা থেকে বীজ ছিটিয়ে খাওয়ার উপযোগী শস্য পাওয়ার ধারণা সৃষ্টি হয় ! কৃষিকাজের এ পর্যায়কে বলা হয় উদ্যান চাষ এক্ষেত্ে পথমে মেয়েরা তাদের বসবাসের আশপাশে পতিত জমিতে একটি লম্বা লাঠি বা পশুর শিং দিয়ে মাটি চিরে গর্তে বীজ ফেলে ফসল ও ফলমূল উতপাদন করত ফসল পাকলে পশুর চোয়ালের হাড় দিয়ে ফসল কাটত তবে প্রয়োজনের বেশি ফসল তারা উতপাদন   করেনি এক জায়গায় বারবার এমন ফসল ফলানো যেত না বলে তাদের জীবন ছিল যাযাবর প্রকৃতির\nপশুপালন সমাজ'),
                    Document(id='0e20af52-47f1-45ad-92c9-ace00defaedc', metadata={'page_start': 43, 'chapter': 'বাংলাদেশের পরিবেশ', 'class_number': 'class_6', 'page_end': 48, 'book_name': 'bgs'}, page_content='passage: বাংলাদেশ ও বিশ্বপরিচয়\n8৭\nনিচের উদ্দীপকটি পড়ে ৩ ও ৪ নং প্রশ্নের উত্তর দাও | আজাদ তার গ্রামে গাছপালা কেটে এবং জলাশয় ভরাট করে একটি সাবানের কারখানা তৈরি করে কারখানার মেশিনের শব্দে আশপাশের   মানুস অতিষ্ঠ আজাদের চাচা চাকরি শেষে গামে এসে খালি জায়়গায় গাছ   লাগানোর পরামর্শ দেন অপরিষ্কার খালগুলো পরিষ্কার করে পানি চলাচলের ব্যবস্থা করেন\n৩ আজাদের কার্যক্রমকে কী বলা যায়? ক মানুষ সৃষ্ট পরিবেশগত সমস্যা খ প্রকৃতি সৃষ্ট পরিবেশগত সমস্যা গ   প্রকৃতিকে মানুষের জয় করার চেষ্টা দ প্রকৃতির উপর মানুষের নির্ভরশীলতা 8. আজাদের চাচার কার্যক্রমের ফলাফল কোনটি? ক সমুদ্রপৃষ্ঠের উচ্চতা বাড়বে খ মাটির উর্বরতা শক্তি কমে যাবে গ. মাটির ক্ষয় বৃদ্ধি পাবে ঘ. জীববৈচিত্র্য রক্ষা পাবে\nসৃজনশীল প্রশ্ন\nক আলো ও তাপের প্রধান উৎস কোনটি? খ . মানুষ কীভাবে প্রকৃতির উপর আধিপত্য বাড়িয়েছে? ব্যাখ্যা করো গ   উপরের চিত্রে কোন সমস্যাটি ফুটে উঠেছে? ব্যাখ্যা করো ঘ. উক্ত সমস্যা সমাধানে তোমাদের মতো শিশুদের করণীয় সম্পর্কে আলোচনা করো\n?')]

retrieved_chunks = [chunk.page_content for chunk in chunks]

user_query = "মাছ চাষ কি?"

# 2. Function to score a chunk using OpenJev
def evaluate_chunk(query, chunk):
    url = "http://localhost:3000/v1/systemone"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "model": "openjev",
        "state": f"User Query: {query}\n\nDocument Chunk: {chunk}",
        "questions": {
            "relevance": {
                "type": "noul",  # "noul" provides a binary yes/no probability distribution
                "instructions": "Is this document chunk directly relevant and helpful to answer the user query?"
            }
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        result = response.json()
        
        # OpenJev returns exact probability distributions for answers
        # Fetching the 'yes' probability score
        yes_prob = result["questions"]["relevance"]["probabilities"].get("yes", 0.0)
        return yes_prob
    except Exception as e:
        print(f"Error evaluating chunk: {e}")
        return 0.0

# 3. Process and rank all chunks
scored_chunks = []
for chunk in retrieved_chunks:
    score = evaluate_chunk(user_query, chunk)
    scored_chunks.append({"chunk": chunk, "score": score})

# 4. Sort by highest relevance score
scored_chunks.sort(key=lambda x: x["score"], reverse=True)

# 5. Filter out low relevance chunks (e.g., threshold of 0.70)
relevance_threshold = 0.70
filtered_chunks = [item for item in scored_chunks if item["score"] >= relevance_threshold]

print("--- Top Ranked & Filtered Chunks ---")
for idx, item in enumerate(filtered_chunks):
    print(f"Rank {idx+1} (Score: {item['score']:.4f}): {item['chunk']}")















{
  "department": {
    "type": "choice",
    "instructions": "Which text is accurate by question",
    "criteria": {
      "returns": "Exchanges, refunds, wrong or damaged items",
      "shipping": "Delivery status, delays, lost packages",
      "billing": "Charges, invoices, payment problems"
    }
  },
  "new_score_1": {
    "type": "score",
    "instructions": "How well does the state meet the bar?",
    "criteria": [
      "Does not meet it",
      "Partially meets it",
      "Meets it",
      "Clearly exceeds it"
    ]
  }
}