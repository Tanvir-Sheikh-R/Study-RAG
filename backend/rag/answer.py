"""Answer generation: retrieved chapter chunks + the student question → Bangla answer."""

from __future__ import annotations

from typing import Any, Iterator

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_deepseek import ChatDeepSeek
from langchain_groq import ChatGroq

from backend.config import LLM_MAX_TOKENS, LLM_MODEL, LLM_MODEL_GROQ, LLM_TEMPERATURE

PROMPT = PromptTemplate.from_template(
    """তুমি একজন বাংলাদেশি শিক্ষক, শিক্ষার্থীদের পাঠ্যবই থেকে পড়াতে সাহায্য করো।
ভদ্র, সহজ ও সহায়ক ভাষায় উত্তর দাও। উত্তর অবশ্যই বাংলায় লিখবে।

শিক্ষার্থীর প্রশ্ন: {query}

পাঠ্যবইয়ের প্রাসঙ্গিক অংশ:
{content}

নিয়ম:
- প্রাথমিক উৎস হিসেবে উপরের পাঠ্যবইয়ের অংশ ব্যবহার করো।
- নিজের জ্ঞান ব্যবহার করতে পারো, তবে তা যত কম হয় তত ভালো; পাঠ্যবইয়ের বাইরের তথ্য যোগ করলে সেটি সংক্ষেপে বলো।
- যদি প্রশ্নের উত্তর উপরের অংশে না থাকে, প্রথমে লিখো: "এই প্রশ্নটি পাঠ্যবইয়ে উল্লেখ নেই।"
  এরপর চাইলে নিজের জ্ঞান থেকে সংক্ষিপ্ত উত্তর দাও।
- কখনো তথ্য বানিয়ে বলবে না (hallucinate করবে না)।"""
)


def build_llm_deepseek(
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: Any,
) -> ChatDeepSeek:
    return ChatDeepSeek(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE if temperature is None else temperature,
        max_tokens=LLM_MAX_TOKENS if max_tokens is None else max_tokens,
        **kwargs,
    )

def build_llm(
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: Any,
) -> ChatGroq:
    return ChatGroq(
        model=LLM_MODEL_GROQ,
        temperature=LLM_TEMPERATURE if temperature is None else temperature,
        max_tokens=LLM_MAX_TOKENS if max_tokens is None else max_tokens,
        **kwargs,
    )



def build_chain():
    return PROMPT | build_llm() | StrOutputParser()


def format_context(chunks: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        heading_bits = [chunk.get("part"), chunk.get("chapter")]
        heading = " → ".join(bit for bit in heading_bits if bit) or "পাঠ্যবই"
        pages = chunk.get("page_start")
        page_note = f" (পৃষ্ঠা {pages})" if pages else ""
        blocks.append(f"[অংশ {index} — {heading}{page_note}]\n{chunk['text']}")
    return "\n\n".join(blocks)


def stream_answer(query: str, chunks: list[dict[str, Any]]) -> Iterator[str]:
    chain = build_chain()
    payload = {"query": query, "content": format_context(chunks)}
    for piece in chain.stream(payload):
        if piece:
            yield piece
