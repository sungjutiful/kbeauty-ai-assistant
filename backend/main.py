import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from routers import chat, conversations, data  # noqa: E402

app = FastAPI(
    title="K-Beauty Trend AI 비서",
    description="Google Trends K-뷰티 성분(PDRN) 검색 관심도 데이터를 이해하고 답하는 AI 비서 API",
    version="1.0.0",
)

origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5500").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(conversations.router)
app.include_router(chat.router)


@app.get("/", tags=["health"])
def health():
    """Render 콜드스타트 확인용 — 프론트가 처음에 이 주소를 호출해 서버를 깨운다."""
    return {"status": "ok"}
