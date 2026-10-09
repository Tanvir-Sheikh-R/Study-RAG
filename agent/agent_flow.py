"""A LangGraph agent whose only tool is the বই বন্ধু textbook RAG search.

Topology:

    START → agent ─┬─(tool calls)→ retrieve → agent
                   └─(no tool calls)→ END

The agent decides when to search and what to search for; `retrieve` runs the same
hybrid BM25 + FAISS retrieval the web app uses and hands the chunks back as a
ToolMessage. State is a plain message list, so `compile(checkpointer=...)` can be
used for multi-turn memory without changing anything else.

CLI:

    python -m agent.agent_flow                             # interactive REPL, default chapter
    python -m agent.agent_flow -q "উৎসব কী কী?"             # one question, then exit
    python -m agent.agent_flow --class-id class_8 --subject science --chapter খাদ্য
    python -m agent.agent_flow --list                      # available class/subject/chapter
"""

from __future__ import annotations

import argparse
import sys
from typing import Annotated, Any, Iterator, Sequence, TypedDict

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from backend.rag import chapters, retriever
from backend.rag.answer import format_context

DEFAULT_SCOPE = {
    "class_id": "class_5",
    "subject": "bangla",
    "chapter": "বৈচিত্র্যময় বাংলাদেশ",
}

MAX_TOOL_ROUNDS = 6
SNIPPET_CHARS = 1800

SYSTEM_PROMPT = """তুমি "বই বন্ধু" — একজন বাংলাদেশি শিক্ষক যে শিক্ষার্থীদের পাঠ্যবই থেকে পড়তে সাহায্য করে।

তোমার হাতে একটি টুল আছে: search_textbook — একটি নির্দিষ্ট অধ্যায়ে হাইব্রিড (BM25 + dense) সার্চ করে পাঠ্যবইয়ের প্রাসঙ্গিক অংশ ফেরত দেয়।

নিয়ম:
- পাঠ্যবইয়ের তথ্য দরকার হলে অবশ্যই search_textbook ব্যবহার করবে; অনুমান করে উত্তর দেবে না।
- প্রশ্নটি যদি অস্পষ্ট হয়, টুলে স্পষ্ট ও পূর্ণ সার্চ-কোয়েরি লিখবে (বাংলায়)।
- উত্তর সবসময় বাংলায় দেবে, সহজ ও শিক্ষার্থীবান্ধব ভাষায়।
- উত্তরের প্রাথমিক উৎস হবে টুল থেকে পাওয়া অংশ। নিজের জ্ঞান ব্যবহার করলে তা সংক্ষেপে এবং স্পষ্টভাবে আলাদা করে বলবে।
- টুল যদি কিছু না পায়, প্রথমে লিখবে: "এই প্রশ্নটি পাঠ্যবইয়ে উল্লেখ নেই।" এরপর চাইলে সংক্ষিপ্ত উত্তর দেবে।
- তথ্য বানিয়ে বলবে না (hallucinate করবে না)।"""


class AgentState(TypedDict):
    """Conversation state: only a message list, extended by `add_messages`."""

    messages: Annotated[list[AnyMessage], add_messages]


def resolve_scope(class_id: str, subject: str, chapter: str) -> dict[str, Any]:
    """Validate a class/subject/chapter choice against chapters.json.

    Returns the resolved book path (class/subject or class/stream/subject) plus
    whether that chapter is indexed, so problems surface before the graph runs.
    """
    scope = chapters.resolve_scope(class_id, None, subject)
    if scope is None:
        streams = chapters.streams_of(class_id)
        available = (
            tuple(
                name for stream in streams for name in chapters.subjects_of(class_id, stream)
            )
            if streams
            else chapters.subjects_of(class_id)
        )
        raise ValueError(
            f"Unknown subject {subject!r} for {class_id!r}. Available: {', '.join(available)}"
        )

    # The vector store is keyed by sub-chapter name where a chapter has sub_chapters,
    # so accept both top-level chapter names and sub-chapter names.
    accepted: list[str] = []
    for item in scope["chapters"]:
        accepted.append(chapters.chapter_label(item))
        accepted.extend(str(sub.get("sub_chapter_name") or "") for sub in (item.get("sub_chapters") or []))

    wanted = chapters.normalize_chapter_ref(chapter)
    match = next(
        (name for name in accepted if chapters.normalize_chapter_ref(name) == wanted),
        None,
    )
    if match is None:
        raise ValueError(
            f"Unknown chapter {chapter!r} in {class_id}/{subject}. Available: {', '.join(accepted)}"
        )

    book = chapters.book_path(class_id, subject, scope["stream"])
    return {
        "class_id": class_id,
        "class_label": chapters.class_label(class_id),
        "subject": subject,
        "subject_label": chapters.subject_label(subject),
        "stream": scope["stream"],
        "book": book,
        "chapter": match,
        "indexed": chapters.find_chapter_dir(book, match) is not None,
    }


def build_search_tool(book: str, chapter: str, k: int = retriever.HYBRID_K) -> BaseTool:
    """Create the single RAG tool, bound to one chapter."""

    @tool("search_textbook")
    def search_textbook(query: str) -> str:
        """Search this chapter of the Bengali textbook and return the most relevant
        passages. Use it for any question that needs information from the book.

        Args:
            query: A focused Bengali search query describing the information needed.
        """
        hits = retriever.search(book, chapter, query, k=k)

        if not hits:
            return (
                f"কোনো প্রাসঙ্গিক অংশ পাওয়া যায়নি ({book} / {chapter})। "
                "পাঠ্যবইয়ে এই প্রশ্নের উত্তর নেই বলে জানাও।"
            )

        body = format_context(hits)[:SNIPPET_CHARS]
        return f"{len(hits)}টি অংশ পাওয়া গেছে ({book} / {chapter}):\n\n{body}"

    return search_textbook


def build_llm(temperature: float = 0.2, max_tokens: int = 2048):
    """The agent's model. DeepSeek is verified to support tool calling here."""
    from backend.rag.answer import build_llm as build_answer_llm

    return build_answer_llm(temperature=temperature, max_tokens=max_tokens)


def build_agent_graph(
    book: str,
    chapter: str,
    *,
    llm: Any | None = None,
    k: int = retriever.HYBRID_K,
    system_prompt: str = SYSTEM_PROMPT,
):
    """Assemble and compile the LangGraph agent for one chapter.

    Pass `llm` to inject a different chat model (it must support bind_tools).
    """
    tools = [build_search_tool(book, chapter, k=k)]
    model = (llm or build_llm()).bind_tools(tools)

    def call_model(state: AgentState) -> dict[str, list[BaseMessage]]:
        messages = list(state["messages"])
        if not any(isinstance(message, SystemMessage) for message in messages):
            messages = [SystemMessage(content=system_prompt), *messages]
        return {"messages": [model.invoke(messages)]}

    def next_step(state: AgentState) -> str:
        """Route to the tool, or stop — and break loops that never answer."""
        tool_rounds = sum(1 for message in state["messages"] if isinstance(message, ToolMessage))
        if tool_rounds >= MAX_TOOL_ROUNDS:
            return END
        return tools_condition(state)

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("retrieve", ToolNode(tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", next_step, {"tools": "retrieve", END: END})
    graph.add_edge("retrieve", "agent")
    return graph.compile()


def _final_text(messages: Sequence[AnyMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and not message.tool_calls:
            return str(message.content).strip()
    return ""


def ask(
    question: str,
    *,
    class_id: str,
    subject: str,
    chapter: str,
    graph: Any | None = None,
    history: Sequence[AnyMessage] | None = None,
) -> dict[str, Any]:
    """Run the agent once and return the answer plus the tool calls it made."""
    scope = resolve_scope(class_id, subject, chapter)
    agent = graph or build_agent_graph(scope["book"], chapter)
    messages: list[AnyMessage] = [*(history or []), HumanMessage(content=question)]
    result = agent.invoke({"messages": messages}, config={"recursion_limit": 40})
    transcript = result["messages"]

    calls: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    for message in transcript:
        if isinstance(message, AIMessage) and message.tool_calls:
            calls.extend({"name": call["name"], "args": call["args"]} for call in message.tool_calls)
        if isinstance(message, ToolMessage):
            outputs.append({"tool_call_id": message.tool_call_id, "content": str(message.content)})

    return {
        "scope": scope,
        "question": question,
        "answer": _final_text(transcript),
        "tool_calls": calls,
        "tool_outputs": outputs,
        "messages": transcript,
    }


def stream(
    question: str,
    *,
    class_id: str,
    subject: str,
    chapter: str,
    graph: Any | None = None,
    history: Sequence[AnyMessage] | None = None,
) -> Iterator[tuple[str, Any]]:
    """Yield ("token", text) for answer text and ("node", name) when a node starts."""
    scope = resolve_scope(class_id, subject, chapter)
    agent = graph or build_agent_graph(scope["book"], chapter)
    messages: list[AnyMessage] = [*(history or []), HumanMessage(content=question)]

    # One pass, two modes: a second .stream() call would run the model twice.
    for mode, payload in agent.stream({"messages": messages}, stream_mode=["messages", "updates"]):
        if mode == "messages":
            chunk = payload[0]
            text = getattr(chunk, "content", "")
            if text:
                yield "token", text
        elif mode == "updates":
            for node in payload:
                yield "node", node


def run_repl(scope: dict[str, Any], show_tools: bool = False) -> None:
    """Interactive loop over one chapter; keeps history in memory."""
    agent = build_agent_graph(scope["book"], scope["chapter"])
    history: list[AnyMessage] = []

    print(f"বই বন্ধু এজেন্ট — {scope['class_label']} · {scope['subject_label']} · {scope['chapter']}")
    print(f"বই: {scope['book']}" + ("" if scope["indexed"] else "  (সূচি নেই — পুরো বই খোঁজা হবে)"))
    print("প্রশ্ন লিখো (বের হতে 'exit' বা Ctrl+C)\n")

    while True:
        try:
            question = input("তুমি: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not question:
            continue
        if question.lower() in {"exit", "quit", "বন্ধ"}:
            return

        print("বই বন্ধু: ", end="", flush=True)
        answer: list[str] = []
        try:
            if show_tools:
                print("\n  [টুল ও মডেল চলছে...]")
            for kind, payload in stream(
                question,
                class_id=scope["class_id"],
                subject=scope["subject"],
                chapter=scope["chapter"],
                graph=agent,
                history=history,
            ):
                if kind == "token":
                    answer.append(str(payload))
                    sys.stdout.write(str(payload))
                    sys.stdout.flush()
            text = "".join(answer).strip()
            if not text:
                text = "(কোনো উত্তর পাওয়া যায়নি)"
                print(text)
        except KeyboardInterrupt:
            print("\n[থামানো হয়েছে]")
            continue
        except Exception as error:  # noqa: BLE001 - a REPL should survive one bad turn
            print(f"\n[সমস্যা] {type(error).__name__}: {error}")
            continue

        print("\n")
        history.append(HumanMessage(content=question))
        history.append(AIMessage(content=text))


def list_scope() -> None:
    """Print every class/subject with its chapter count, for picking a scope."""
    for class_id in chapters.known_classes():
        print(f"\n{chapters.class_label(class_id)}  ({class_id})")
        streams = chapters.streams_of(class_id)
        entries = (
            [(stream, subject) for stream in streams for subject in chapters.subjects_of(class_id, stream)]
            if streams
            else [(None, subject) for subject in chapters.subjects_of(class_id)]
        )
        for stream, subject in entries:
            book = chapters.book_path(class_id, subject, stream)
            count = len(chapters.chapters_of(class_id, stream, subject))
            prefix = f"{stream}/" if stream else ""
            mark = "" if chapters.book_has_vectors(book) else "  (সূচি নেই)"
            print(f"  {prefix}{subject:32s} {count:3d} chapters{mark}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="বই বন্ধু LangGraph RAG agent")
    parser.add_argument("-q", "--question", help="ask one question and exit")
    parser.add_argument("--class-id", default=DEFAULT_SCOPE["class_id"])
    parser.add_argument("--subject", default=DEFAULT_SCOPE["subject"])
    parser.add_argument("--chapter", default=DEFAULT_SCOPE["chapter"])
    parser.add_argument("--k", type=int, default=retriever.HYBRID_K, help="chunks per search")
    parser.add_argument("--show-tools", action="store_true", help="print tool activity")
    parser.add_argument("--list", action="store_true", help="list classes, subjects and chapters")
    args = parser.parse_args(argv)

    if args.list:
        list_scope()
        return 0

    try:
        scope = resolve_scope(args.class_id, args.subject, args.chapter)
    except ValueError as error:
        print(f"ভুল নির্বাচন: {error}", file=sys.stderr)
        return 2

    if args.question:
        try:
            result = ask(
                args.question,
                class_id=args.class_id,
                subject=args.subject,
                chapter=args.chapter,
            )
        except Exception as error:  # noqa: BLE001 - CLI should report, not traceback
            print(f"সমস্যা: {type(error).__name__}: {error}", file=sys.stderr)
            return 1

        if args.show_tools:
            for call in result["tool_calls"]:
                print(f"[tool] {call['name']}({call['args']})", file=sys.stderr)
        print(result["answer"] or "(কোনো উত্তর পাওয়া যায়নি)")
        return 0

    run_repl(scope, show_tools=args.show_tools)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
