import hashlib
import hmac
import json
import urllib.parse


def check_init_data(init_data: str, bot_token: str):
    """Проверка подписи Telegram Mini App."""
    try:
        pairs = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received = pairs.pop("hash", None)
        if not received:
            return None
        data_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calc = hmac.new(secret, data_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc, received):
            return None
        return json.loads(pairs["user"])
    except Exception:
        return None
