"""데이터 API — CRUD 4개 + summary 1개."""
from fastapi import APIRouter, HTTPException

from schemas import DataIn, DataOut
from services.firebase import get_db
from services.summary import build_summary

router = APIRouter(prefix="/api/data", tags=["data"])
COLLECTION = "data"


def _to_out(doc) -> dict:
    d = doc.to_dict()
    return {"id": doc.id, "date": d["date"], "value": d["value"], "memo": d.get("memo", "")}


def _all_rows() -> list[dict]:
    docs = get_db().collection(COLLECTION).order_by("date").stream()
    return [_to_out(doc) for doc in docs]


# summary는 /{id} 보다 먼저 선언
@router.get("/summary")
def get_summary():
    return build_summary(_all_rows())


@router.get("", response_model=list[DataOut])
def list_data():
    return _all_rows()


@router.post("", response_model=DataOut, status_code=201)
def create_data(item: DataIn):
    payload = {"date": item.date.isoformat(), "value": item.value, "memo": item.memo}
    _, ref = get_db().collection(COLLECTION).add(payload)
    return {"id": ref.id, **payload}


@router.put("/{item_id}", response_model=DataOut)
def update_data(item_id: str, item: DataIn):
    ref = get_db().collection(COLLECTION).document(item_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")
    payload = {"date": item.date.isoformat(), "value": item.value, "memo": item.memo}
    ref.set(payload)
    return {"id": item_id, **payload}


@router.delete("/{item_id}")
def delete_data(item_id: str):
    ref = get_db().collection(COLLECTION).document(item_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")
    ref.delete()
    return {"deleted": item_id}
