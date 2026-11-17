"""Separate profile-bound bearer capabilities; only a digest is stored."""
import hashlib
import hmac
from datetime import datetime, timezone
from fastapi import HTTPException


def require_profile_access(handler, profile_id: str, authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="프로필 접근 토큰이 필요합니다.")
    token = authorization[7:]
    if not token or len(token) > 200:
        raise HTTPException(status_code=403, detail="프로필 접근 권한이 없습니다.")
    if not handler or not handler.is_connected:
        raise HTTPException(status_code=503, detail="데이터베이스에 연결되지 않았습니다.")
    record = handler.get_collection("user_profiles").find_one({"profile_id": profile_id, "is_active": True})
    digest = hashlib.sha256(token.encode()).hexdigest()
    expected = (record or {}).get("access_token_hash")
    expires = (record or {}).get("access_token_expires_at")
    if isinstance(expires, str):
        try:
            expires = datetime.fromisoformat(expires)
        except ValueError:
            expires = None
    # PyMongo returns naive UTC datetimes unless tz_aware is configured.
    if isinstance(expires, datetime) and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if (not record or not record.get("is_active") or not isinstance(expires, datetime)
            or expires <= datetime.now(timezone.utc)
            or not isinstance(expected, str) or not hmac.compare_digest(digest, expected)):
        raise HTTPException(status_code=403, detail="프로필 접근 권한이 없습니다.")
