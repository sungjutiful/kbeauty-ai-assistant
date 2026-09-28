"""Firestore 연결.

서비스 계정 키는 코드에 넣지 않고 환경 변수로 읽는다.
- FIREBASE_SERVICE_ACCOUNT_JSON : 키 JSON 전체를 한 줄 문자열로 (Render 배포용)
- FIREBASE_SERVICE_ACCOUNT_PATH : 키 파일 경로 (로컬 개발용)
"""
import json
import os

import firebase_admin
from firebase_admin import credentials, firestore

_db = None


def get_db():
    global _db
    if _db is not None:
        return _db

    if not firebase_admin._apps:
        raw_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        key_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

        if raw_json:
            cred = credentials.Certificate(json.loads(raw_json))
        elif key_path:
            cred = credentials.Certificate(key_path)
        else:
            raise RuntimeError(
                "Firebase 키가 없습니다. FIREBASE_SERVICE_ACCOUNT_JSON 또는 "
                "FIREBASE_SERVICE_ACCOUNT_PATH 환경 변수를 설정하세요."
            )
        firebase_admin.initialize_app(cred)

    _db = firestore.client()
    return _db
