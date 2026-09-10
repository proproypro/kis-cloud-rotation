"""섹터 순환매 → 종목 스윙 실전 집행기 (모의계좌).

지금 데이터로 선도 섹터 → 강한 종목 3개 선정(+국면필터) → 모의계좌 리밸런싱.
주 1회 실행 권장. 기본 dry(미리보기), 'live'로만 실제 모의주문.

사용법: python sector_live.py         (미리보기)
        python sector_live.py live    (모의주문 실행)
"""
import sys

import FinanceDataReader as fdr

import config
import kis_order
from kis_balance import get_balance
from sector_rotation import ETFS               # {etf코드: 섹터명}
from sector_stocks import SECTOR_STOCKS        # {etf코드: [종목코드...]}

LOOKBACK, SEC_K, STOCK_N, MA_REGIME = 20, 1, 3, 200
CASH_USE = 0.95     # 가용현금의 95%까지 투입


def series(code):
    try:
        df = fdr.DataReader(code, "2024-06-01")
        return [float(c) for c in df["Close"].tolist() if c == c]
    except Exception:
        return []


def mom(C, lb=LOOKBACK):
    return C[-1] / C[-1 - lb] - 1 if len(C) > lb else None


def name_of(code):
    for etf, codes in SECTOR_STOCKS.items():
        if code in codes:
            return f"{ETFS[etf]}"
    return ""


def select():
    ks = series("KS11")
    regime_ok = len(ks) >= MA_REGIME and ks[-1] > sum(ks[-MA_REGIME:]) / MA_REGIME
    # 섹터 모멘텀
    sm = []
    for etf in SECTOR_STOCKS:
        m = mom(series(etf))
        if m is not None:
            sm.append((m, etf))
    sm.sort(reverse=True)
    lead = [e for m, e in sm[:SEC_K] if m > 0]
    # 선도섹터 내 강한 종목
    picks = []
    for etf in lead:
        cand = []
        for c in SECTOR_STOCKS[etf]:
            m = mom(series(c))
            if m is not None and m > 0:
                cand.append((m, c))
        cand.sort(reverse=True)
        picks += [(c, m) for m, c in cand[:STOCK_N]]
    return regime_ok, sm[:5], lead, picks


def main():
    live = "live" in sys.argv[1:]
    print("=" * 58)
    print(f"  섹터 순환매 스윙 — {'LIVE(모의주문)' if live else 'dry(미리보기)'}")
    print("=" * 58)
    regime_ok, top_sec, lead, picks = select()

    print("\n[섹터 모멘텀 상위]")
    for m, etf in top_sec:
        mark = "◀ 선도" if etf in lead else ""
        print(f"  {ETFS[etf]:8} {m:+.1%} {mark}")
    print(f"\n[시장 국면] 코스피 200일선 {'위 → 매수 OK' if regime_ok else '아래 → 현금(신규 매수 중단)'}")

    if not regime_ok:
        print("\n하락장이라 오늘은 신규 진입 없음. (현금 유지)")
        return
    if not picks:
        print("\n조건 맞는 종목 없음.")
        return

    hold, summary = get_balance()
    held = {h["종목코드"]: h for h in hold}
    universe = {c for codes in SECTOR_STOCKS.values() for c in codes}
    target = [c for c, _ in picks]
    print(f"\n[선정 종목] (선도섹터: {', '.join(ETFS[e] for e in lead)})  목표: {', '.join(target)}")

    # 리밸런싱: 우리 전략 종목 중 목표에서 빠진 보유분 매도
    to_sell = [c for c in held if c in universe and c not in target]
    to_buy = [c for c in target if c not in held]

    print("\n[리밸런싱 계획]")
    if to_sell:
        for c in to_sell:
            print(f"  매도 {held[c]['종목명']}({c}) {held[c]['보유수량']}주 (목표 이탈)")
    if not to_buy:
        print("  신규 매수 없음 (이미 목표 종목 보유 중)")

    if live:
        print("\n[LIVE] 매도 실행...")
        for c in to_sell:
            try:
                r = kis_order.order(c, held[c]["보유수량"], "sell")
                print(f"  매도 {c} → {r['메시지']}")
            except Exception as e:
                print(f"  매도 {c} 오류: {e}")
        _, summary = get_balance()   # 매도 후 현금 갱신

    cash = summary["주문가능현금"]
    budget = int(cash * CASH_USE / len(to_buy)) if to_buy else 0
    from kis_price import get_price
    plan = []
    for code in to_buy:
        try:
            px = get_price(code)["현재가"]
        except Exception as e:
            print(f"  {code} 현재가 오류: {e}"); continue
        qty = budget // px
        plan.append((code, qty, px))
        print(f"  매수예정 {code} {name_of(code)}  현재가 {px:,}  → {qty}주 (~{qty*px:,}원)")

    if not live:
        print("\n[dry] 실제 주문 안 함. 실행하려면: python sector_live.py live")
        return
    print("\n[LIVE] 매수 실행...")
    for code, qty, px in plan:
        if qty < 1:
            continue
        try:
            r = kis_order.order(code, qty, "buy")
            print(f"  매수 {code} {qty}주 → {r['메시지']} (주문번호 {r['주문번호']})")
        except Exception as e:
            print(f"  매수 {code} 오류: {e}")
    print("\n리밸런싱 완료.")


if __name__ == "__main__":
    main()
