"""시계열 데이터 → 요약 정보 (프롬프트 주입용)."""


def _avg(values):
    return round(sum(values) / len(values), 1) if values else 0.0


def build_summary(rows: list[dict]) -> dict:
    """rows: [{"date": "YYYY-MM-DD", "value": int, "memo": str}, ...]"""
    if not rows:
        return {"keyword": None, "period": None, "count": 0, "metrics": {}, "trend": "데이터 없음", "recent": []}

    rows = sorted(rows, key=lambda r: r["date"])
    values = [r["value"] for r in rows]

    max_row = max(rows, key=lambda r: r["value"])
    min_row = min(rows, key=lambda r: r["value"])
    latest = rows[-1]

    # 최근 추세: 최근 4주 평균 vs 직전 4주 평균
    last4 = values[-4:]
    prev4 = values[-8:-4]
    last4_avg, prev4_avg = _avg(last4), _avg(prev4)
    if prev4_avg == 0:
        change = 0.0 if last4_avg == 0 else 100.0
    else:
        change = round((last4_avg - prev4_avg) / prev4_avg * 100, 1)

    if change >= 5:
        direction = "상승"
    elif change <= -5:
        direction = "하락"
    else:
        direction = "유지"

    return {
        "keyword": latest.get("memo"),
        "period": f"{rows[0]['date']} ~ {latest['date']}",
        "count": len(rows),
        "metrics": {
            "average": _avg(values),
            "max": max_row["value"],
            "max_date": max_row["date"],
            "min": min_row["value"],
            "min_date": min_row["date"],
            "latest": latest["value"],
            "latest_date": latest["date"],
            "peak_ratio_pct": round(latest["value"] / max_row["value"] * 100, 1) if max_row["value"] else 0,
        },
        "trend": f"{direction} (최근 4주 평균 {last4_avg}, 직전 4주 대비 {change:+}%)",
        # AI가 '최근 몇 주' 질문에 답할 수 있도록 최근 8주 값 포함
        "recent": [{"date": r["date"], "value": r["value"]} for r in rows[-8:]],
    }
