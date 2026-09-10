"""국장 섹터 순환매 로테이션 백테스트.

15개 섹터 ETF를 모멘텀으로 순위 매겨, 강한 상위 K개 섹터로 주기적 로테이션.
"순환매 도는 섹터로 갈아타기"가 그냥 버티기를 이기는지 검증.
"""
import json
import os
import sys

import FinanceDataReader as fdr

SEC_DIR = os.path.join(os.path.dirname(__file__), "data", "sector")
COST = 0.0003

ETFS = {
    "091160": "반도체", "091180": "자동차", "091170": "은행", "244580": "바이오",
    "117460": "에너지화학", "140710": "운송", "102970": "증권", "117700": "건설",
    "266360": "IT", "305720": "2차전지", "228790": "화장품", "227560": "헬스케어",
    "139290": "경기소비재", "139270": "철강소재",
}


def load_all(start="2019-01-01"):
    os.makedirs(SEC_DIR, exist_ok=True)
    data = {}
    for code in list(ETFS) + ["KS11"]:
        p = os.path.join(SEC_DIR, f"{code}.json")
        if os.path.exists(p):
            rows = json.load(open(p, encoding="utf-8"))
        else:
            df = fdr.DataReader(code, start)
            rows = [{"d": i.strftime("%Y%m%d"), "c": float(r["Close"])}
                    for i, r in df.iterrows() if r["Close"] == r["Close"]]
            json.dump(rows, open(p, "w", encoding="utf-8"))
        data[code] = {"C": [r["c"] for r in rows], "pos": {r["d"]: i for i, r in enumerate(rows)},
                      "D": [r["d"] for r in rows]}
    return data


def simulate(data, lookback, topk, rebal):
    master = data["091160"]["D"]
    codes = list(ETFS)
    start = lookback + 5
    eq, held = 1.0, []
    peak, mdd = 1.0, 0.0
    for t in range(start, len(master)):
        d, dp = master[t], master[t - 1]
        if (t - start) % rebal == 0:
            dsig = master[t - 1]          # 전일 종가로 신호 계산(미래참조 방지)
            scored = []
            for c in codes:
                pos = data[c]["pos"]
                if dsig in pos and pos[dsig] >= lookback:
                    i = pos[dsig]
                    mom = data[c]["C"][i] / data[c]["C"][i - lookback] - 1
                    scored.append((mom, c))
            scored.sort(reverse=True)
            newheld = [c for _, c in scored[:topk] if scored and _ > 0]  # 모멘텀 양수만
            if set(newheld) != set(held):
                eq *= (1 - COST)
                held = newheld
        # 일일 수익 (보유 섹터 평균)
        if held:
            rs = []
            for c in held:
                pos = data[c]["pos"]
                if d in pos and dp in pos:
                    rs.append(data[c]["C"][pos[d]] / data[c]["C"][pos[dp]] - 1)
            if rs:
                eq *= (1 + sum(rs) / len(rs))
        peak = max(peak, eq); mdd = min(mdd, eq / peak - 1)
    n = len(master) - start
    return {"tot": eq - 1, "cagr": (eq) ** (252 / n) - 1, "mdd": mdd, "n": n}


def bench(data, codes):
    """동일비중 매수후보유 (섹터 전체)."""
    master = data["091160"]["D"]
    start = 5
    eq, peak, mdd = 1.0, 1.0, 0.0
    for t in range(start, len(master)):
        d, dp = master[t], master[t - 1]
        rs = []
        for c in codes:
            pos = data[c]["pos"]
            if d in pos and dp in pos:
                rs.append(data[c]["C"][pos[d]] / data[c]["C"][pos[dp]] - 1)
        if rs:
            eq *= (1 + sum(rs) / len(rs))
        peak = max(peak, eq); mdd = min(mdd, eq / peak - 1)
    n = len(master) - start
    return {"tot": eq - 1, "cagr": eq ** (252 / n) - 1, "mdd": mdd}


def main():
    print("데이터 로딩(캐시)...")
    data = load_all()
    n = data["091160"]["D"]
    print(f"기간 {n[0]} ~ {n[-1]}  섹터 {len(ETFS)}개\n")

    b = bench(data, list(ETFS))
    ks_c = data["KS11"]["C"]
    ks_tot = ks_c[-1] / ks_c[0] - 1
    print(f"[벤치] 섹터 동일비중 버티기: 총 {b['tot']:+.0%}  CAGR {b['cagr']:+.1%}  MDD {b['mdd']:+.0%}")
    print(f"[벤치] 코스피 버티기        : 총 {ks_tot:+.0%}\n")

    print(f"{'룩백/보유/주기':22}{'총수익':>9}{'CAGR':>8}{'MDD':>8}")
    print("-" * 47)
    for lb in (20, 40, 60):
        for tk in (1, 2, 3):
            r = simulate(data, lb, tk, rebal=5)   # 주1회 로테이션
            print(f"{f'{lb}일/{tk}개/주1회':22}{r['tot']:>+9.0%}{r['cagr']:>+8.1%}{r['mdd']:>+8.0%}")


if __name__ == "__main__":
    main()
