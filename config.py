"""설정 로더 — .env 파일에서 앱키/시크릿/계좌번호를 읽어옵니다.

비밀 값은 코드에 직접 쓰지 않고 항상 .env 에서 불러옵니다.
"""
import os
from dotenv import load_dotenv

load_dotenv()  # 같은 폴더의 .env 파일을 읽어 환경변수로 로드

# --- KIS 도메인 ---
# 시세(현재가 등) 조회는 실전 도메인이 가장 안정적이라 실전을 사용합니다.
# 주문/잔고는 아래 TRADE_BASE(모의 or 실전)를 사용합니다.
REAL_BASE = "https://openapi.koreainvestment.com:9443"
MOCK_BASE = "https://openapivts.koreainvestment.com:29443"

APP_KEY = os.getenv("KIS_APP_KEY", "").strip()
APP_SECRET = os.getenv("KIS_APP_SECRET", "").strip()
ACCOUNT_NO = os.getenv("KIS_ACCOUNT_NO", "").strip()
ENV = os.getenv("KIS_ENV", "mock").strip().lower()

# 주문/잔고에 사용할 도메인 (환경에 따라 결정)
TRADE_BASE = MOCK_BASE if ENV == "mock" else REAL_BASE
# 시세 조회용 도메인.
# 이 앱키는 모의투자 전용이라 시세도 모의 도메인으로 보내야 함(실전 도메인은 EGW02004 거부).
QUOTE_BASE = TRADE_BASE


def account_parts():
    """계좌번호를 앞 8자리(CANO)와 뒤 2자리(ACNT_PRDT_CD)로 분리."""
    no = ACCOUNT_NO.replace("-", "").strip()
    if len(no) < 10:
        return "", ""
    return no[:8], no[8:10]


def check():
    """필수 설정이 채워졌는지 확인."""
    missing = []
    if not APP_KEY or APP_KEY.startswith("여기에"):
        missing.append("KIS_APP_KEY")
    if not APP_SECRET or APP_SECRET.startswith("여기에"):
        missing.append("KIS_APP_SECRET")
    if missing:
        raise SystemExit(
            f"[설정 오류] .env 에 다음 값을 채워주세요: {', '.join(missing)}\n"
            f"(.env.example 을 복사해서 .env 로 만드세요)"
        )
