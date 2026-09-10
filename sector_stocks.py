"""섹터 순환매 → 종목 단위 트레이딩.

1) 섹터 ETF 20일 모멘텀으로 선도 섹터 포착 (검증된 신호)
2) 선도 섹터 '안'에서 20일 모멘텀 강한 종목 N개 보유, 주1회 로테이션
비교: 섹터ETF 로테이션 / 코스피
"""
import json
import os
import sys

import FinanceDataReader as fdr

from sector_rotation import load_all as load_etfs, ETFS, COST

SW_DIR = os.path.join(os.path.dirname(__file__), "data", "swing")
SS_DIR = os.path.join(os.path.dirname(__file__), "data", "sector_stocks")

# 섹터ETF코드 -> 대표 종목코드들
SECTOR_STOCKS = {
    "091160": ["005930", "000660", "042700", "000990", "058470"],           # 반도체
    "091180": ["005380", "000270", "012330", "204320", "011210"],           # 자동차
    "091170": ["105560", "055550", "086790", "316140", "024110"],           # 은행
    "244580": ["207940", "068270", "000100", "128940", "326030"],           # 바이오
    "117460": ["051910", "011170", "011780", "009830", "010950"],           # 에너지화학
    "140710": ["003490", "011200", "028670", "000120"],                     # 운송
    "102970": ["006800", "016360", "005940", "039490", "071050"],           # 증권
    "117700": ["000720", "006360", "375500", "047040", "294870"],           # 건설
    "266360": ["035420", "035720", "018260", "036570", "053800"],           # IT
    "305720": ["373220", "006400", "003670", "247540", "066970"],           # 2차전지
    "228790": ["090430", "051900", "192820", "161890", "241710"],           # 화장품
    "139290": ["139480", "023530", "004170", "383220", "008770"],           # 경기소비재
    "139270": ["005490", "004020", "010130", "460860", "103140"],           # 철강소재
}


def load_stock(code):
    # 1) swing 캐시  2) sector_stocks 캐시  3) FDR 신규
    for base, key in ((SW_DIR, "close"), (SS_DIR, "close")):
        p = os.path.join(base, f"{code}.json")
        if os.path.exists(p):
            rows = json.load(open(p, encoding="utf-8"))
            return {"C": [r[key] for r in rows], "pos": {r["date"]: i for i, r in enumerate(rows)}}
    os.makedirs(SS_DIR, exist_ok=True)
    try:
        df = fdr.DataReader(code, "2019-01-01")
        rows = [{"date": i.strftime("%Y%m%d"), "close": float(r["Close"])}
                for i, r in df.iterrows() if r["Close"] == r["Close"]]
        json.dump(rows, open(os.path.join(SS_DIR, f"{code}.json"), "w", encoding="utf-8"))
        return {"C": [r["close"] for r in rows], "pos": {r["date"]: i for i, r in enumerate(rows)}}
    except Exception:
        return None


def mom(series, d, lb):
    i = series["pos"].get(d)
    if i is None or i < lb:
        return None
    return series["C"][i] / series["C"][i - lb] - 1


def dret(series, d, dp):
    a, b = series["pos"].get(d), series["pos"].get(dp)
    if a is None or b is None:
        return None
    return series["C"][a] / series["C"][b] - 1


def sma_at(series, d, n):
    i = series["pos"].get(d)
    if i is None or i < n - 1:
        return None
    return sum(series["C"][i - n + 1:i + 1]) / n


def run(lookback=20, sec_k=1, stock_n=3, rebal=5, use_regime=False, use_stop=False):
    etfs = load_etfs()
    ks = etfs["KS11"]
    stocks = {}
    for codes in SECTOR_STOCKS.values():
        for c in codes:
            if c not in stocks:
                s = load_stock(c)
                if s:
                    stocks[c] = s
    master = etfs["091160"]["D"]
    start = lookback + 5
    eq, held, peak, mdd = 1.0, [], 1.0, 0.0
    for t in range(start, len(master)):
        d, dp = master[t], master[t - 1]
        # 국면(전일 기준): 코스피 > 200일선
        regime_ok = True
        if use_regime:
            m200 = sma_at(ks, dp, 200)
            ip = ks["pos"].get(dp)
            regime_ok = (m200 is not None and ip is not None and ks["C"][ip] > m200)

        # 개별 손절: 전일 종가가 20일선 아래인 보유종목 청산
        if use_stop and held:
            keep = []
            for c in held:
                ma = sma_at(stocks[c], dp, 20)
                ip = stocks[c]["pos"].get(dp)
                if ma is not None and ip is not None and stocks[c]["C"][ip] < ma:
                    eq *= (1 - COST)          # 청산
                else:
                    keep.append(c)
            held = keep

        # 하락장이면 전량 현금
        if use_regime and not regime_ok and held:
            eq *= (1 - COST); held = []

        # 주1회 리밸런싱 (국면 OK일 때만 신규)
        if (t - start) % rebal == 0 and (not use_regime or regime_ok):
            dsig = master[t - 1]
            sm = []
            for etf in SECTOR_STOCKS:
                m = mom(etfs[etf], dsig, lookback)
                if m is not None:
                    sm.append((m, etf))
            sm.sort(reverse=True)
            lead = [e for m, e in sm[:sec_k] if m > 0]
            target = []
            for etf in lead:
                cand = []
                for c in SECTOR_STOCKS[etf]:
                    if c in stocks:
                        m = mom(stocks[c], dsig, lookback)
                        if m is not None and m > 0:
                            cand.append((m, c))
                cand.sort(reverse=True)
                target += [c for m, c in cand[:stock_n]]
            if set(target) != set(held):
                eq *= (1 - COST); held = target

        if held:
            rs = [dret(stocks[c], d, dp) for c in held if dret(stocks[c], d, dp) is not None]
            if rs:
                eq *= (1 + sum(rs) / len(rs))
        peak = max(peak, eq); mdd = min(mdd, eq / peak - 1)
    n = len(master) - start
    return {"tot": eq - 1, "cagr": eq ** (252 / n) - 1, "mdd": mdd}


if __name__ == "__main__":
    lb = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    ks = load_etfs()["KS11"]["C"]
    print(f"섹터→종목 트레이딩 (룩백 {lb}일, 1섹터/3종목, 주1회)")
    print(f"[벤치] 코스피: {ks[-1]/ks[0]-1:+.0%}\n")
    print(f"{'낙폭제어':24}{'총수익':>9}{'CAGR':>8}{'MDD':>8}")
    print("-" * 49)
    configs = [
        ("① 기본(제어 없음)", dict()),
        ("② +국면필터", dict(use_regime=True)),
        ("③ +국면+손절", dict(use_regime=True, use_stop=True)),
        ("④ +손절만", dict(use_stop=True)),
    ]
    for name, kw in configs:
        r = run(lb, 1, 3, **kw)
        print(f"{name:24}{r['tot']:>+9.0%}{r['cagr']:>+8.1%}{r['mdd']:>+8.0%}")
