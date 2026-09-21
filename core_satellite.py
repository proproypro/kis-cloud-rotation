"""코어+위성 자산배분 실행기 (모의계좌).

코어 75% = 영구포트폴리오(50%) + HAA-KR(50%)   ※ 공개 전략, 원저자 규칙 그대로 (검증: quant/taa.py)
위성 25% = KODEX 200 (SATELLITE_MODE='halloween' 이면 11~4월만 보유)

- 신호: '직전 완료된 달'의 월말 종가(야후 미국 ETF + 코스피) → 한 달 내내 같은 목표 → 매일 돌려도 안전(멱등)
- 매매: 목표 대비 BAND 이상 벌어진 종목만 조정. 신규편입/편출은 즉시.
- 전략 외 보유분(기존 섹터 순환매 종목)은 매도 대상.

사용법: python core_satellite.py         (미리보기, 주문 없음)
        python core_satellite.py live    (모의주문 실행)
"""
import sys
import time

import FinanceDataReader as fdr
import pandas as pd

CORE, SAT = 0.75, 0.25
SATELLITE_MODE = "hold"          # 'hold' | 'halloween'
BAND = 0.02                      # 총자산의 2% 이상 벌어지면 조정
CASH_BUFFER = 0.01               # 시장가 체결 오차 대비 현금 1% 남김
HAA_TOP = 4

# 신호용 자산 → 국내 상장 ETF (하루 거래대금 수억 이상만 채택)
ETF = {
    "SPY": ("360750", "TIGER 미국S&P500"),
    "QQQ": ("133690", "TIGER 미국나스닥100"),
    "EFA": ("251350", "KODEX MSCI선진국"),
    "KOSPI": ("069500", "KODEX 200"),
    "GLD": ("411060", "ACE KRX금현물"),
    "IEF": ("305080", "TIGER 미국채10년선물"),
    "TLT": ("476760", "ACE 미국30년국채액티브"),
    "SHY": ("329750", "TIGER 미국달러단기채권액티브"),
}
PERMANENT = {"SPY": 0.25, "TLT": 0.25, "GLD": 0.25, "SHY": 0.25}
HAA_OFFENSIVE = ["SPY", "QQQ", "EFA", "KOSPI", "GLD", "IEF", "TLT"]
YAHOO = ["SPY", "QQQ", "EFA", "GLD", "IEF", "TLT", "SHY", "TIP"]


def _retry(fn, tries=4, wait=3):
    for i in range(tries):
        try:
            return fn()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(wait)


def month_end_prices():
    """완료된 달들의 월말 종가. (진행 중인 달은 버림 → 실행 시각·시계 오차와 무관)"""
    d = {}
    for t in YAHOO:
        df = _retry(lambda t=t: fdr.DataReader(f"YAHOO:{t}", "2024-01-01"))
        d[t] = df["Adj Close"] if "Adj Close" in df else df["Close"]
    d["KOSPI"] = _retry(lambda: fdr.DataReader("KS11", "2024-01-01"))["Close"]
    px = pd.DataFrame(d).sort_index().ffill().dropna()
    me = px.groupby([px.index.year, px.index.month]).tail(1)
    return me.iloc[:-1], px.index[-1]          # 마지막 행 = 진행 중인 달


def haa_weights(me):
    s = sum(me.iloc[-1] / me.iloc[-1 - n] - 1 for n in (1, 3, 6, 12)) / 4
    safe = "IEF" if s["IEF"] > s["SHY"] else "SHY"
    w = {}
    if s["TIP"] <= 0:
        w[safe] = 1.0
    else:
        for a in s[HAA_OFFENSIVE].nlargest(HAA_TOP).index:
            k = a if s[a] > 0 else safe
            w[k] = w.get(k, 0) + 1.0 / HAA_TOP
    return w, s, safe


def target_weights():
    me, last = month_end_prices()
    if len(me) < 13:
        raise SystemExit("신호 계산에 필요한 13개월 데이터 부족")
    haa, score, safe = haa_weights(me)
    w = {}
    for a, x in PERMANENT.items():
        w[a] = w.get(a, 0) + CORE * 0.5 * x
    for a, x in haa.items():
        w[a] = w.get(a, 0) + CORE * 0.5 * x
    sat_on = SATELLITE_MODE == "hold" or last.month in (11, 12, 1, 2, 3, 4)
    if sat_on:
        w["KOSPI"] = w.get("KOSPI", 0) + SAT
    else:
        w["SHY"] = w.get("SHY", 0) + SAT
    return w, {"signal_month": me.index[-1].strftime("%Y-%m"), "haa": haa, "score": score,
               "safe": safe, "canary": score["TIP"], "sat_on": sat_on}


def main():
    live = "live" in sys.argv[1:]
    print("=" * 64)
    print(f"  코어+위성 자산배분 — {'LIVE(모의주문)' if live else 'dry(미리보기)'}")
    print("=" * 64)
    w, info = target_weights()
    print(f"\n[신호] 기준월 {info['signal_month']} 월말   카나리아 TIP {info['canary']:+.2%} → "
          f"{'공격' if info['canary'] > 0 else '방어(전부 ' + info['safe'] + ')'}")
    print("  HAA 모멘텀(1·3·6·12개월 평균): " +
          "  ".join(f"{a} {info['score'][a]:+.1%}" for a in info["score"][HAA_OFFENSIVE].sort_values(ascending=False).index))
    print("  HAA 선택: " + ", ".join(f"{ETF[a][1]} {x:.0%}" for a, x in info["haa"].items()))

    from kis_balance import get_balance
    from kis_price import get_price
    import kis_order
    hold, summary = _retry(get_balance)
    held = {h["종목코드"]: h for h in hold}
    equity = summary["총평가금액"]
    code_w = {ETF[a][0]: x for a, x in w.items()}
    names = {c: n for c, n in ETF.values()}

    print(f"\n[계좌] 총평가 {equity:,}원   주문가능현금 {summary['주문가능현금']:,}원")
    print(f"\n{'종목':28}{'목표':>7}{'현재':>7}{'차이':>8}   조치")
    plan = []                                      # (code, side, qty, 사유)
    for code, h in held.items():
        if code not in code_w:
            plan.append((code, "sell", h["보유수량"], "전략 외 보유"))
            print(f"{h['종목명'][:14]+'('+code+')':28}{0:>7.1%}{h['평가금액']/equity:>7.1%}{-h['평가금액']/equity:>+8.1%}   전량 매도(전략 외)")
    for code, tw in sorted(code_w.items(), key=lambda x: -x[1]):
        cur_amt = held[code]["평가금액"] if code in held else 0
        diff = tw - cur_amt / equity
        px = held[code]["현재가"] if code in held else _retry(lambda code=code: get_price(code))["현재가"]
        act = "유지"
        if abs(diff) >= BAND or (cur_amt == 0 and tw > 0):
            qty = int(abs(diff) * equity * (1 - CASH_BUFFER if diff > 0 else 1) // px)
            if qty > 0:
                side = "buy" if diff > 0 else "sell"
                plan.append((code, side, qty, "비중 조정"))
                act = f"{'매수' if diff > 0 else '매도'} {qty}주 (~{qty*px:,}원)"
        print(f"{names[code][:14]+'('+code+')':28}{tw:>7.1%}{cur_amt/equity:>7.1%}{diff:>+8.1%}   {act}")

    if not plan:
        print("\n목표 비중 범위 안 — 매매 없음.")
        return
    if not live:
        print("\n[dry] 실제 주문 안 함. 실행하려면: python core_satellite.py live")
        return

    sells = [p for p in plan if p[1] == "sell"]
    buys = [p for p in plan if p[1] == "buy"]
    print("\n[LIVE] 매도...")
    for code, _, qty, why in sells:
        try:
            r = _retry(lambda code=code, qty=qty: kis_order.order(code, qty, "sell"))
            print(f"  매도 {code} {qty}주 ({why}) → {r['메시지']}")
        except Exception as e:
            print(f"  매도 {code} 오류: {e}")
    if sells and buys:
        print("[대기] 매도대금 반영 확인...")
        for _ in range(16):
            time.sleep(30)
            try:
                _, s2 = _retry(get_balance)
            except Exception:
                continue
            summary = s2
            if s2["주문가능현금"] > 0.5 * sum(code_w[c] for c, _, _, _ in buys) * equity:
                break
    cash = summary["주문가능현금"]
    print(f"[LIVE] 매수... (주문가능현금 {cash:,}원)")
    for code, _, qty, why in buys:
        try:
            px = _retry(lambda code=code: get_price(code))["현재가"]
            qty = min(qty, int(cash * (1 - CASH_BUFFER) // px))
            if qty < 1:
                print(f"  매수 {code} 건너뜀(현금 부족) — 다음 실행에서 자동 보완")
                continue
            r = _retry(lambda code=code, qty=qty: kis_order.order(code, qty, "buy"))
            cash -= qty * px
            print(f"  매수 {code} {qty}주 → {r['메시지']}")
        except Exception as e:
            print(f"  매수 {code} 오류: {e}")
    print("\n완료. (미체결·부족분은 다음 실행 때 목표와의 차이로 자동 보완)")


if __name__ == "__main__":
    main()
