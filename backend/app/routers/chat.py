from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import Conversation, Message, User
from app.schemas import ChatRequest, ChatResponse, ConversationOut, MessageOut
from app.services.llm import LLMClient, get_llm_client
from app.services.rag import answer_question

router = APIRouter(tags=["chat"])

Llm = Annotated[LLMClient | None, Depends(get_llm_client)]


def _own_conversation(db: DbSession, user: User, conversation_id: int) -> Conversation:
    conv = db.get(Conversation, conversation_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conv


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, db: DbSession, user: CurrentUser, llm: Llm) -> ChatResponse:
    if body.conversation_id is not None:
        conv = _own_conversation(db, user, body.conversation_id)
    else:
        conv = Conversation(user_id=user.id, title=body.question.strip()[:80])
        db.add(conv)
        db.flush()

    history = [{"role": m.role, "content": m.content} for m in conv.messages]
    result = answer_question(db, user, body.question, llm, history)
    sources = [s.as_dict() for s in result.sources]

    db.add(Message(conversation_id=conv.id, role="user", content=body.question))
    db.add(Message(conversation_id=conv.id, role="assistant", content=result.answer, sources=sources))
    db.commit()

    return ChatResponse(
        conversation_id=conv.id,
        answer=result.answer,
        sources=sources,
        corrected_query=result.corrected_query,
        grounded=result.grounded,
    )


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: DbSession, user: CurrentUser) -> list[Conversation]:
    return list(
        db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user.id)
            .order_by(Conversation.created_at.desc())
        )
    )


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(conversation_id: int, db: DbSession, user: CurrentUser) -> list[Message]:
    return _own_conversation(db, user, conversation_id).messages


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: int, db: DbSession, user: CurrentUser) -> None:
    db.delete(_own_conversation(db, user, conversation_id))
    db.commit()
