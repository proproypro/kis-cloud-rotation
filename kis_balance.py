"""국내주식 잔고/자산 조회 (읽기 전용).

모의계좌에 든 현금(예수금)과 보유 종목을 조회합니다.
계좌번호(.env의 KIS_ACCOUNT_NO)가 올바른지도 함께 검증됩니다.
"""
import requests

import config
from kis_auth import get_token

# 잔고조회 TR: 모의=VTTC8434R, 실전=TTTC8434R
TR_ID = "VTTC8434R" if config.ENV == "mock" else "TTTC8434R"


def get_balance():
    """(보유종목 리스트, 요약 dict) 를 반환."""
    base = config.TRADE_BASE
    token = get_token(base)
    cano, prdt = config.account_parts()
    if not cano:
        raise SystemExit("[설정 오류] .env의 KIS_ACCOUNT_NO 형식을 확인하세요 (예: 50123456-01)")

    url = f"{base}/uapi/domestic-stock/v1/trading/inquire-balance"
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": config.APP_KEY,
        "appsecret": config.APP_SECRET,
        "tr_id": TR_ID,
        "custtype": "P",
    }
    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": prdt,
        "AFHR_FLPR_YN": "N",       # 시간외단일가 여부
        "OFL_YN": "",
        "INQR_DVSN": "02",         # 02: 종목별
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("rt_cd") != "0":
        raise RuntimeError(f"잔고조회 실패: {data.get('msg1')} (msg_cd={data.get('msg_cd')})")

    holdings = []
    for it in data.get("output1", []):
        qty = int(it["hldg_qty"])
        if qty == 0:
            continue
        holdings.append({
            "종목명": it["prdt_name"],
            "종목코드": it["pdno"],
            "보유수량": qty,
            "매입평균가": float(it["pchs_avg_pric"]),
            "현재가": int(it["prpr"]),
            "평가손익": int(it["evlu_pfls_amt"]),
            "손익률": float(it["evlu_pfls_rt"]),
            "평가금액": int(it["evlu_amt"]),
        })

    summary_raw = data.get("output2", [{}])[0]
    summary = {
        "예수금": int(summary_raw.get("dnca_tot_amt", 0)),          # 현금
        "주문가능현금": int(summary_raw.get("prvs_rcdl_excc_amt", 0)),
        "총평가금액": int(summary_raw.get("tot_evlu_amt", 0)),       # 현금+주식
        "매입금액합계": int(summary_raw.get("pchs_amt_smtl_amt", 0)),
        "평가손익합계": int(summary_raw.get("evlu_pfls_smtl_amt", 0)),
    }
    return holdings, summary


if __name__ == "__main__":
    holdings, summary = get_balance()
    print("=" * 60)
    print("[ 계좌 요약 ]")
    print(f"  예수금(현금)   : {summary['예수금']:>15,} 원")
    print(f"  주문가능현금   : {summary['주문가능현금']:>15,} 원")
    print(f"  총평가금액     : {summary['총평가금액']:>15,} 원")
    print(f"  평가손익합계   : {summary['평가손익합계']:>15,} 원")
    print("=" * 60)
    if holdings:
        print("[ 보유 종목 ]")
        for h in holdings:
            print(
                f"  {h['종목명']}({h['종목코드']})  "
                f"{h['보유수량']}주  현재가 {h['현재가']:,}  "
                f"손익 {h['평가손익']:+,}원 ({h['손익률']:+.2f}%)"
            )
    else:
        print("[ 보유 종목 ] 없음 (아직 매수 안 함)")
