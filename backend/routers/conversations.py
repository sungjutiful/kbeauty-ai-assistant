"""대화 기록 API.

불러오기 방식: (A) GET /api/conversations/{id} 로 전체 messages 조회.
목록 조회(GET /api/conversations)에는 messages를 포함하지 않는다.
"""
from fastapi import APIRouter, HTTPException
from google.cloud.firestore import SERVER_TIMESTAMP

from schemas import ConversationDetail, ConversationIn, ConversationSummary
from services.firebase import get_db

router = APIRouter(prefix="/api/conversations", tags=["conversations"])
COLLECTION = "conversations"


def _ts(value):
    return value.isoformat() if hasattr(value, "isoformat") else None


def _summary(doc) -> dict:
    d = doc.to_dict()
    return {
        "id": doc.id,
        "title": d.get("title", "(제목 없음)"),
        "message_count": len(d.get("messages", [])),
        "updated_at": _ts(d.get("updated_at")),
    }


@router.post("", response_model=ConversationSummary, status_code=201)
def create_conversation(conv: ConversationIn):
    messages = [m.model_dump() for m in conv.messages]
    title = conv.title or messages[0]["content"][:30]
    _, ref = get_db().collection(COLLECTION).add(
        {"title": title, "messages": messages, "updated_at": SERVER_TIMESTAMP}
    )
    return {"id": ref.id, "title": title, "message_count": len(messages), "updated_at": None}


@router.get("", response_model=list[ConversationSummary])
def list_conversations():
    docs = (
        get_db().collection(COLLECTION)
        .order_by("updated_at", direction="DESCENDING")
        .limit(50)
        .stream()
    )
    return [_summary(doc) for doc in docs]


@router.get("/{conv_id}", response_model=ConversationDetail)
def get_conversation(conv_id: str):
    doc = get_db().collection(COLLECTION).document(conv_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
    return {**_summary(doc), "messages": doc.to_dict().get("messages", [])}


@router.delete("/{conv_id}")
def delete_conversation(conv_id: str):
    ref = get_db().collection(COLLECTION).document(conv_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
    ref.delete()
    return {"deleted": conv_id}
