import base64
from hashlib import sha256
import hmac
import json
import time
from urllib.parse import parse_qsl

INIT_DATA_TTL = 600
SESSION_TTL = 8 * 60 * 60


class TelegramAuth:
    def __init__(self, bot_token: str):
        self.telegram_key = hmac.digest(b"WebAppData", bot_token.encode(), sha256)
        self.session_key = hmac.digest(b"AfterTheDay session v1", bot_token.encode(), sha256)

    def verify_init_data(self, raw: str, *, now: int | None = None) -> int:
        if not raw or len(raw) > 8192:
            raise ValueError("invalid init data")
        pairs = parse_qsl(raw, strict_parsing=True, max_num_fields=30)
        fields = dict(pairs)
        digest = fields.pop("hash", "")
        if len(pairs) != len(fields) + 1 or len(digest) != 64 or not digest.isascii():
            raise ValueError("invalid init data")
        check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
        expected = hmac.digest(self.telegram_key, check_string.encode(), sha256).hex()
        if not hmac.compare_digest(expected, digest):
            raise ValueError("invalid init data signature")
        verified_at = int(time.time()) if now is None else now
        try:
            age = verified_at - int(fields["auth_date"])
            owner = json.loads(fields["user"])["id"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid Telegram identity") from exc
        if not -30 <= age <= INIT_DATA_TTL or type(owner) is not int or not 0 < owner < 2**52:
            raise ValueError("expired or invalid Telegram identity")
        return owner

    def issue(self, owner: int) -> str:
        payload = f"{owner}.{int(time.time()) + SESSION_TTL}"
        signature = base64.urlsafe_b64encode(hmac.digest(self.session_key, payload.encode(), sha256)).decode()
        return f"{payload}.{signature}"

    def verify_session(self, token: str) -> int:
        if len(token) > 150 or not token.isascii():
            raise ValueError("invalid session")
        owner, expiry, signature = token.split(".")
        payload = f"{owner}.{expiry}"
        expected = base64.urlsafe_b64encode(hmac.digest(self.session_key, payload.encode(), sha256)).decode()
        if not hmac.compare_digest(signature, expected) or int(expiry) <= int(time.time()):
            raise ValueError("expired session")
        return int(owner)
