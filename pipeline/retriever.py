"""pipeline/retriever.py — Stage 5: scoped hybrid retrieval + LLM answer."""
from __future__ import annotations

import logging

from langchain_core.documents import Document

from settings.config import Config

log = logging.getLogger(__name__)


def build_hybrid_retriever(
    vectorstore,
    chunks: list[Document],
    class_number: str | None = None,
    book_name: str | None = None,
    chapter: str | None = None,
):
    """
    Build a hybrid BM25 + dense retriever, scoped to the requested book/chapter.

    Examples
    --------
    # Whole vectorstore (no filter):
    retriever = build_hybrid_retriever(vectorstore, all_chunks)

    # Scope to one book:
    retriever = build_hybrid_retriever(vectorstore, all_chunks, class_number="class_6", book_name="bgs")

    # Scope to one chapter:
    retriever = build_hybrid_retriever(vectorstore, all_chunks, class_number="class_6", book_name="bgs", chapter="মাছ চাষ")
    """
    from pipeline.store_manager import get_scoped_retriever
    return get_scoped_retriever(vectorstore, chunks, class_number, book_name, chapter)


def build_answer_chain():
    from langchain_core.prompts import PromptTemplate
    from langchain_deepseek import ChatDeepSeek

    prompt = PromptTemplate.from_template(Config.ANSWER_PROMPT)
    llm = ChatDeepSeek(
        model=Config.LLM_MODEL,
        temperature=Config.LLM_TEMPERATURE,
        max_tokens=Config.LLM_MAX_TOKENS,
    )
    return prompt | llm


def search(retriever, query: str) -> list[Document]:
    """Always applies the e5 query prefix before retrieval."""
    return retriever.invoke(Config.E5_QUERY_PREFIX + query)


def answer(retriever, chain, query: str) -> str:
    docs = search(retriever, query)
    return chain.invoke({"query": query, "content": docs}).content
