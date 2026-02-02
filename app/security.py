import base64
import hashlib
import hmac
import os
import secrets


PBKDF2_ITERATIONS = 600_000
SESSION_COOKIE_NAME = "session_id"


def _get_session_secret() -> bytes:
    secret = os.getenv("SESSION_SECRET")
    if not secret:
        raise RuntimeError("SESSION_SECRET is not set")
    return secret.encode("utf-8")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256$%d$%s$%s" % (
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    parts = stored_hash.split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    try:
        iterations = int(parts[1])
    except ValueError:
        return False
    salt = base64.b64decode(parts[2].encode("ascii"))
    expected = base64.b64decode(parts[3].encode("ascii"))
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(digest, expected)


def sign_session_id(session_id: str) -> str:
    secret = _get_session_secret()
    signature = hmac.new(secret, session_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return signature


def encode_session_cookie(session_id: str) -> str:
    signature = sign_session_id(session_id)
    return f"{session_id}.{signature}"


def decode_session_cookie(cookie_value: str | None) -> str | None:
    if not cookie_value:
        return None
    if "." not in cookie_value:
        return None
    session_id, signature = cookie_value.rsplit(".", 1)
    if not session_id or not signature:
        return None
    expected = sign_session_id(session_id)
    if not hmac.compare_digest(expected, signature):
        return None
    return session_id
