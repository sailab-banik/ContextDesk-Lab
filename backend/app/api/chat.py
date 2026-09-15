"""Chat routes: one message in, a response and its execution record out."""

from fastapi import APIRouter

from app.api.dependencies import ChatServiceDep
from app.models.chat import (
    ChatRequest,
    ChatResponse,
    ComparisonRequest,
    ComparisonResponse,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def send_message(request: ChatRequest, chat_service: ChatServiceDep) -> ChatResponse:
    return await chat_service.handle_message(request)


@router.post("/compare", response_model=ComparisonResponse)
async def compare_configurations(
    request: ComparisonRequest, chat_service: ChatServiceDep
) -> ComparisonResponse:
    """Experiment mode: the same message run across component configurations."""
    return await chat_service.compare(request)
