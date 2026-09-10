"""국내 주식 현재가 조회 (읽기 전용).

가장 안전한 API — 계좌를 건드리지 않고 시세만 읽어옵니다.
연동이 제대로 됐는지 확인하는 용도로 딱 좋습니다.
"""
import requests

import config
from kis_auth import get_token


def get_price(stock_code):
    """종목코드(6자리 문자열)의 현재 시세 정보를 dict 로 반환.

    예) get_price("005930")  # 삼성전자
    """
    base = config.QUOTE_BASE
    token = get_token(base)

    url = f"{base}/uapi/domestic-stock/v1/quotations/inquire-price"
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": config.APP_KEY,
        "appsecret": config.APP_SECRET,
        "tr_id": "FHKST01010100",  # 주식현재가 시세 TR
        "custtype": "P",           # 개인
    }
    params = {
        "fid_cond_mrkt_div_code": "J",   # J: 주식
        "fid_input_iscd": stock_code,
    }
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("rt_cd") != "0":
        raise RuntimeError(f"조회 실패: {data.get('msg1')} (msg_cd={data.get('msg_cd')})")

    out = data["output"]
    return {
        "종목코드": stock_code,
        "현재가": int(out["stck_prpr"]),
        "전일대비": int(out["prdy_vrss"]),
        "등락률": float(out["prdy_ctrt"]),
        "시가": int(out["stck_oprc"]),
        "고가": int(out["stck_hgpr"]),
        "저가": int(out["stck_lwpr"]),
        "거래량": int(out["acml_vol"]),
        "시가총액": out.get("hts_avls", ""),  # 억 단위 문자열
    }


if __name__ == "__main__":
    # 몇 종목 테스트
    samples = {
        "005930": "삼성전자",
        "000660": "SK하이닉스",
        "035720": "카카오",
    }
    for code, name in samples.items():
        try:
            p = get_price(code)
            sign = "▲" if p["전일대비"] > 0 else ("▼" if p["전일대비"] < 0 else "-")
            print(
                f"{name}({code})  "
                f"{p['현재가']:>9,}원  "
                f"{sign}{abs(p['전일대비']):,} ({p['등락률']:+.2f}%)  "
                f"거래량 {p['거래량']:,}"
            )
        except Exception as e:
            print(f"{name}({code})  조회 오류: {e}")
