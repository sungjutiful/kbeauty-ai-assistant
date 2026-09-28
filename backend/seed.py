"""CSV → Firestore 'data' 컬렉션에 한 번 업로드.

사용법:  python seed.py            (기본: PDRN)
        python seed.py Ectoin     (다른 성분)
        python seed.py PDRN --reset   (기존 data 컬렉션 비우고 다시 업로드)
"""
import csv
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from services.firebase import get_db  # noqa: E402

CSV_PATH = Path(__file__).parent / "data" / "merged_processed.csv"
KEYWORDS = {"PDRN", "Ectoin", "Exosome"}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    keyword = args[0] if args else "PDRN"
    if keyword not in KEYWORDS:
        sys.exit(f"키워드는 {KEYWORDS} 중 하나여야 합니다.")

    col = get_db().collection("data")

    if "--reset" in sys.argv:
        for doc in col.stream():
            doc.reference.delete()
        print("기존 data 컬렉션 삭제 완료")

    with open(CSV_PATH, encoding="utf-8") as f:
        rows = [{"date": r["date"], "value": int(r[keyword]), "memo": keyword} for r in csv.DictReader(f)]

    batch = get_db().batch()
    for i, row in enumerate(rows, start=1):
        batch.set(col.document(), row)
        if i % 400 == 0:  # Firestore batch 최대 500건
            batch.commit()
            batch = get_db().batch()
    batch.commit()
    print(f"{keyword} 데이터 {len(rows)}건 업로드 완료")


if __name__ == "__main__":
    main()
