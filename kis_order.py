"""국내주식 현금 주문 (매수/매도).

⚠️ 실제 주문이 체결됩니다. 지금은 모의투자(가짜돈)라 안전하지만,
   KIS_ENV=real 로 바꾸면 진짜 돈이 나갑니다. 항상 확인 후 실행하세요.
"""
import json

import requests

import config
from kis_auth import get_token

# 주문 TR ID (모의 vs 실전)
if config.ENV == "mock":
    TR_BUY = "VTTC0802U"   # 모의 매수
    TR_SELL = "VTTC0801U"  # 모의 매도
else:
    TR_BUY = "TTTC0802U"   # 실전 매수
    TR_SELL = "TTTC0801U"  # 실전 매도


def _hashkey(body: dict) -> str:
    """주문 본문에 대한 위변조 방지 해시 생성."""
    url = f"{config.TRADE_BASE}/uapi/hashkey"
    headers = {
        "content-type": "application/json; charset=utf-8",
        "appkey": config.APP_KEY,
        "appsecret": config.APP_SECRET,
    }
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
    resp.raise_for_status()
    return resp.json()["HASH"]


def order(stock_code: str, qty: int, side: str, price: int = 0):
    """주문 실행.

    stock_code : 종목코드 6자리 (예: "005930")
    qty        : 수량
    side       : "buy" 또는 "sell"
    price      : 지정가(원). 0 이면 시장가 주문.
    """
    base = config.TRADE_BASE
    token = get_token(base)
    cano, prdt = config.account_parts()

    tr_id = TR_BUY if side == "buy" else TR_SELL
    ord_dvsn = "01" if price == 0 else "00"  # 01=시장가, 00=지정가

    body = {
        "CANO": cano,
        "ACNT_PRDT_CD": prdt,
        "PDNO": stock_code,
        "ORD_DVSN": ord_dvsn,
        "ORD_QTY": str(qty),
        "ORD_UNPR": str(price),
    }
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": config.APP_KEY,
        "appsecret": config.APP_SECRET,
        "tr_id": tr_id,
        "custtype": "P",
        "hashkey": _hashkey(body),
    }
    url = f"{base}/uapi/domestic-stock/v1/trading/order-cash"
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("rt_cd") != "0":
        raise RuntimeError(f"주문 실패: {data.get('msg1')} (msg_cd={data.get('msg_cd')})")

    out = data.get("output", {})
    return {
        "성공": True,
        "메시지": data.get("msg1"),
        "주문번호": out.get("ODNO"),
        "주문시각": out.get("ORD_TMD"),
    }


def buy(stock_code, qty, price=0):
    return order(stock_code, qty, "buy", price)


def sell(stock_code, qty, price=0):
    return order(stock_code, qty, "sell", price)


if __name__ == "__main__":
    # 안전장치: 인자로 실행 방식을 명시해야만 주문이 나갑니다.
    import sys
    if len(sys.argv) < 4:
        print("사용법: python kis_order.py [buy|sell] 종목코드 수량 [지정가]")
        print("예) python kis_order.py buy 005930 1        (삼성전자 1주 시장가 매수)")
        print("예) python kis_order.py buy 005930 1 230000 (23만원 지정가 1주 매수)")
        sys.exit(0)

    side = sys.argv[1]
    code = sys.argv[2]
    qty = int(sys.argv[3])
    price = int(sys.argv[4]) if len(sys.argv) > 4 else 0

    env_label = "모의투자" if config.ENV == "mock" else "!!! 실전투자 !!!"
    kind = "시장가" if price == 0 else f"지정가 {price:,}원"
    print(f"[{env_label}] {code} {qty}주 {side} ({kind}) 주문 실행...")
    result = order(code, qty, side, price)
    print("결과:", result)
