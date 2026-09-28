"""Pydantic 모델 — 요청 데이터 검증."""
from datetime import date as Date
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------- data ----------
class DataIn(BaseModel):
    date: Date = Field(..., description="주 시작일 (YYYY-MM-DD)")
    value: int = Field(..., ge=0, le=100, description="Google Trends 검색 관심도 (0~100)")
    memo: str = Field("PDRN", max_length=100)


class DataOut(BaseModel):
    id: str
    date: str
    value: int
    memo: str


# ---------- conversations ----------
class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class ConversationIn(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    messages: list[Message] = Field(..., min_length=1)


class ConversationSummary(BaseModel):
    """목록 조회용 — messages는 포함하지 않는다."""
    id: str
    title: str
    message_count: int
    updated_at: Optional[str] = None


class ConversationDetail(ConversationSummary):
    messages: list[Message]


# ---------- chat ----------
class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    conversation_id: Optional[str] = Field(None, description="이어서 대화할 때만 전달")


class ChatOut(BaseModel):
    reply: str
    conversation_id: str
