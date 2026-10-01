from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

GROUP_PATTERN = r"^[a-z0-9_-]{1,50}$"


def _normalize_groups(groups: list[str]) -> list[str]:
    import re

    cleaned = sorted({g.strip().lower() for g in groups if g and g.strip()})
    for g in cleaned:
        if not re.match(GROUP_PATTERN, g):
            raise ValueError(f"Invalid group name: {g!r} (use a-z, 0-9, '-' or '_')")
    return cleaned


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Users ----------
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    groups: list[str]


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    full_name: str = ""
    role: str = Field(default="user", pattern="^(admin|user)$")
    groups: list[str] = []

    @field_validator("groups")
    @classmethod
    def _groups(cls, v: list[str]) -> list[str]:
        return _normalize_groups(v)


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = Field(default=None, pattern="^(admin|user)$")
    groups: list[str] | None = None

    @field_validator("groups")
    @classmethod
    def _groups(cls, v: list[str] | None) -> list[str] | None:
        return None if v is None else _normalize_groups(v)


# ---------- Documents ----------
class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    filename: str
    content_type: str
    allowed_groups: list[str]
    n_chunks: int
    created_at: datetime


# ---------- Chat ----------
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: int | None = None


class SourceOut(BaseModel):
    ref: int
    document_id: int
    document_title: str
    page: int | None
    snippet: str
    score: float


class ChatResponse(BaseModel):
    conversation_id: int
    answer: str
    sources: list[SourceOut]
    corrected_query: str | None = None
    grounded: bool


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    sources: list[SourceOut] | None
    created_at: datetime
