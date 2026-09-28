"""AI 챗봇 API — 컨텍스트 주입.

흐름: 데이터 요약 조회 → 시스템 프롬프트에 삽입 → GPT 호출 → conversations에 자동 저장
"""
import json
import os

from fastapi import APIRouter, HTTPException
from google.cloud.firestore import SERVER_TIMESTAMP
from openai import OpenAI

from routers.data import get_summary
from schemas import ChatIn, ChatOut
from services.firebase import get_db

router = APIRouter(prefix="/api", tags=["chat"])

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "400"))
HISTORY_LIMIT = 10  # 이전 대화는 최근 10개 메시지만 전달 (토큰 절약)

_client = None


def _openai():
    global _client
    if _client is None:
        if not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY가 설정되지 않았습니다.")
        _client = OpenAI()
    return _client


def build_system_prompt(s: dict) -> str:
    m = s.get("metrics", {})
    recent = ", ".join(f"{r['date']}: {r['value']}" for r in s.get("recent", []))
    return f"""당신은 K-뷰티 성분 트렌드 분석 비서입니다.
아래는 Google Trends 주간 검색 관심도 데이터(0~100, 기간 내 최고점=100)의 요약입니다.

[사용자 데이터 요약]
- 키워드: {s.get('keyword')}
- 데이터 기간: {s.get('period')}
- 총 레코드: {s.get('count')}개 (주 단위)
- 평균: {m.get('average')}
- 최고: {m.get('max')} ({m.get('max_date')})
- 최저: {m.get('min')} ({m.get('min_date')})
- 최신: {m.get('latest')} ({m.get('latest_date')}), 최고점 대비 {m.get('peak_ratio_pct')}%
- 최근 트렌드: {s.get('trend')}
- 최근 8주 값: {recent}

규칙:
- 위 데이터에 근거해서 답하고, 숫자를 인용할 때는 날짜도 함께 말하세요.
- 추세를 말할 때는 '최근 트렌드'의 판정(상승/하락/유지)과 다르게 해석하지 마세요.
- 데이터에 없는 내용은 추측이라고 밝히세요.
- 값은 실제 검색 횟수가 아니라 상대 지수라는 점을 필요할 때 설명하세요.
- 3~5문장으로 간결하게 한국어로 답하세요."""


@router.post("/chat", response_model=ChatOut)
def chat(req: ChatIn):
    db = get_db()
    col = db.collection("conversations")

    # 1) 데이터 요약 조회
    summary = get_summary()

    # 2) 기존 대화 불러오기 (이어서 대화하는 경우)
    history: list[dict] = []
    ref = None
    if req.conversation_id:
        ref = col.document(req.conversation_id)
        doc = ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
        history = doc.to_dict().get("messages", [])

    # 3) 요약을 시스템 프롬프트에 삽입 → GPT 호출
    messages = [{"role": "system", "content": build_system_prompt(summary)}]
    messages += history[-HISTORY_LIMIT:]
    messages.append({"role": "user", "content": req.message})

    try:
        res = _openai().chat.completions.create(
            model=MODEL, messages=messages, max_tokens=MAX_TOKENS, temperature=0.4
        )
        reply = res.choices[0].message.content.strip()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 응답 실패: {e}")

    # 4) conversations에 자동 저장
    new_messages = history + [
        {"role": "user", "content": req.message},
        {"role": "assistant", "content": reply},
    ]
    if ref is None:
        _, ref = col.add({
            "title": req.message[:30],
            "messages": new_messages,
            "updated_at": SERVER_TIMESTAMP,
        })
    else:
        ref.update({"messages": new_messages, "updated_at": SERVER_TIMESTAMP})

    return {"reply": reply, "conversation_id": ref.id}
