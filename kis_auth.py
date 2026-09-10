"""KIS 접근토큰(access token) 발급 + 캐싱.

KIS 토큰은 24시간 유효하고, 너무 자주 재발급하면 오류가 납니다.
그래서 발급받은 토큰을 token_cache.json 에 저장해두고 재사용합니다.
"""
import json
import os
import time

import requests

import config

CACHE_FILE = os.path.join(os.path.dirname(__file__), "token_cache.json")


def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_token(base_url):
    """base_url(실전/모의)에 대한 유효한 access token 을 반환.

    캐시에 살아있는 토큰이 있으면 재사용하고, 없으면 새로 발급받습니다.
    """
    config.check()
    cache = _load_cache()
    entry = cache.get(base_url)

    now = time.time()
    # 만료 10분 전까지는 캐시된 토큰 재사용
    if entry and entry.get("expire_at", 0) - 600 > now:
        return entry["access_token"]

    # 새로 발급
    url = f"{base_url}/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": config.APP_KEY,
        "appsecret": config.APP_SECRET,
    }
    resp = requests.post(url, json=body, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if "access_token" not in data:
        raise RuntimeError(f"토큰 발급 실패: {data}")

    token = data["access_token"]
    expires_in = int(data.get("expires_in", 86400))
    cache[base_url] = {
        "access_token": token,
        "expire_at": now + expires_in,
    }
    _save_cache(cache)
    return token


if __name__ == "__main__":
    # 단독 실행하면 실전 도메인 토큰을 발급해 앞부분만 출력
    t = get_token(config.QUOTE_BASE)
    print("토큰 발급 성공! (앞 20자리만 표시)")
    print(t[:20] + "...")
