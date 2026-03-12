"""
REST API for conversation management.

Endpoints:
  GET    /api/v1/conversations          — List user conversations
  GET    /api/v1/conversations/{id}      — Get conversation with recent messages
  GET    /api/v1/conversations/{id}/messages — Get messages (paginated)
  DELETE /api/v1/conversations/{id}      — Delete a conversation
  PATCH  /api/v1/conversations/{id}      — Update title or metadata
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from pydantic import BaseModel

from src.auth.dependencies import get_current_user_flexible
from src.engine.conversation_service import conversation_service

router = APIRouter(prefix="/conversations", tags=["Conversations"])


class ConversationListItem(BaseModel):
    id: str
    title: Optional[str] = None
    chain_id: Optional[str] = None
    model: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConversationListResponse(BaseModel):
    conversations: list[ConversationListItem]
    total: int


class MessageItem(BaseModel):
    id: str
    role: str
    content: str
    model: Optional[str] = None
    tokens_used: int = 0
    task_id: Optional[str] = None
    metadata: dict = {}
    created_at: Optional[datetime] = None


class ConversationDetail(BaseModel):
    id: str
    title: Optional[str] = None
    chain_id: Optional[str] = None
    model: Optional[str] = None
    metadata: dict = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    messages: list[MessageItem] = []
    message_count: int = 0


class ConversationPatch(BaseModel):
    title: Optional[str] = None
    metadata: Optional[dict] = None


def _get_user_id(current_user: dict) -> str:
    return current_user.get("email", "anonymous")


@router.get("")
async def list_conversations(
    limit: int = QueryParam(50, ge=1, le=200),
    offset: int = QueryParam(0, ge=0),
    current_user: dict = Depends(get_current_user_flexible),
) -> ConversationListResponse:
    user_id = _get_user_id(current_user)
    convs, total = await conversation_service.list_conversations(user_id, limit, offset)
    return ConversationListResponse(
        conversations=[
            ConversationListItem(
                id=c.id,
                title=c.title,
                chain_id=c.chain_id,
                model=c.model,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in convs
        ],
        total=total,
    )


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user_flexible),
) -> ConversationDetail:
    conv = await conversation_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_id = _get_user_id(current_user)
    if conv.user_id != user_id and user_id != "anonymous":
        raise HTTPException(status_code=403, detail="Access denied")

    messages = await conversation_service.get_history(conversation_id, limit=50)
    count = await conversation_service.count_messages(conversation_id)

    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        chain_id=conv.chain_id,
        model=conv.model,
        metadata=conv.metadata,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[
            MessageItem(
                id=m.id, role=m.role, content=m.content,
                model=m.model, tokens_used=m.tokens_used,
                task_id=m.task_id, metadata=m.metadata or {},
                created_at=m.created_at,
            )
            for m in messages
        ],
        message_count=count,
    )


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    limit: int = QueryParam(100, ge=1, le=500),
    before: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user_flexible),
) -> list[MessageItem]:
    conv = await conversation_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_id = _get_user_id(current_user)
    if conv.user_id != user_id and user_id != "anonymous":
        raise HTTPException(status_code=403, detail="Access denied")

    messages = await conversation_service.get_history(conversation_id, limit, before)
    return [
        MessageItem(
            id=m.id, role=m.role, content=m.content,
            model=m.model, tokens_used=m.tokens_used,
            task_id=m.task_id, metadata=m.metadata or {},
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user_flexible),
):
    conv = await conversation_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_id = _get_user_id(current_user)
    if conv.user_id != user_id and user_id != "anonymous":
        raise HTTPException(status_code=403, detail="Access denied")

    await conversation_service.delete_conversation(conversation_id)
    return {"status": "deleted", "id": conversation_id}


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    patch: ConversationPatch,
    current_user: dict = Depends(get_current_user_flexible),
):
    conv = await conversation_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_id = _get_user_id(current_user)
    if conv.user_id != user_id and user_id != "anonymous":
        raise HTTPException(status_code=403, detail="Access denied")

    if patch.title is not None:
        await conversation_service.update_title(conversation_id, patch.title)

    updated = await conversation_service.get_conversation(conversation_id)
    return {
        "id": updated.id,
        "title": updated.title,
        "updated_at": updated.updated_at,
    }
