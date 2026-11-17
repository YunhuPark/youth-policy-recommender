"""Reserve policy fan-out atomically across local processes and threads."""
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
from fastapi import HTTPException


def reserve_policy_calls(count: int, client_ip: str) -> None:
    if count < 1 or count > 10:
        raise HTTPException(status_code=422, detail="정책은 1~10개까지 설명할 수 있습니다.")
    location = Path(os.getenv("AI_BUDGET_DB") or Path(__file__).resolve().parents[1] / ".runtime" / "ai-budget.db")
    location.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    day, minute = now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%dT%H:%M")
    daily_limit = int(os.getenv("AI_DAILY_POLICY_LIMIT", "200"))
    minute_limit = int(os.getenv("AI_IP_MINUTE_POLICY_LIMIT", "20"))
    with sqlite3.connect(str(location), timeout=10) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS usage (scope TEXT, period TEXT, used INTEGER NOT NULL, PRIMARY KEY(scope, period))")
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM usage WHERE (scope = 'global' AND period < ?) OR (scope != 'global' AND period < ?)", (day, minute))
        limits = [("global", day, daily_limit), ("ip:" + client_ip, minute, minute_limit)]
        for scope, period, limit in limits:
            row = conn.execute("SELECT used FROM usage WHERE scope=? AND period=?", (scope, period)).fetchone()
            if (row[0] if row else 0) + count > limit:
                raise HTTPException(status_code=429, detail="AI 설명 사용 한도에 도달했습니다.")
        for scope, period, _ in limits:
            conn.execute("INSERT INTO usage VALUES (?, ?, ?) ON CONFLICT(scope, period) DO UPDATE SET used=used+excluded.used", (scope, period, count))
