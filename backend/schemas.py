"""Pydantic request/response models for the বই বন্ধু API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ChapterContext(BaseModel):
    class_id: str = Field(min_length=1)
    class_label: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    subject_label: str = Field(min_length=1)
    stream: str | None = None
    book: str = Field(min_length=1)
    chapter: str = Field(min_length=1)

    @property
    def title(self) -> str:
        return f"{self.chapter} · {self.subject_label} · {self.class_label}"


class ThreadCreate(BaseModel):
    context: ChapterContext


class ThreadContextUpdate(BaseModel):
    context: ChapterContext


class ChatMessageIn(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("message must not be blank")
        return cleaned


class ChatStart(ChatMessageIn):
    context: ChapterContext


class MessageOut(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ThreadSummary(BaseModel):
    thread_id: str
    title: str
    context: dict[str, Any]
    message_count: int
    preview: str
    created_at: str
    updated_at: str


class ThreadDetail(BaseModel):
    thread_id: str
    title: str
    context: dict[str, Any]
    messages: list[MessageOut]
    created_at: str
    updated_at: str


class ThreadGroup(BaseModel):
    label: str
    threads: list[ThreadSummary]


class HealthOut(BaseModel):
    status: Literal["ok"]
    embedding_model: str
    device: str
    dimension: int
    indexed_books: int
    named_books: int
    llm_model: str
