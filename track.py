"""포트폴리오 스냅샷 기록기 — 매일 계좌 상태를 history에 저장(자산곡선용)."""
import json
import os
from datetime import datetime

from kis_balance import get_balance

HIST = os.path.join(os.path.dirname(__file__), "data", "portfolio_history.json")
STATE = os.path.join(os.path.dirname(__file__), "data", "strategy_state.json")
INIT = 100_000_000


def save_strategy_state(today):
    """대시보드용: 이번 달 신호·목표비중. 하루 1회만 계산(야후 호출 절약), 실패해도 기록은 계속."""
    try:
        if os.path.exists(STATE) and json.load(open(STATE, encoding="utf-8")).get("computed") == today:
            return
        import core_satellite as cs
        w, info = cs.target_weights()
        half = cs.CORE * 0.5
        targets = []
        for a, tw in sorted(w.items(), key=lambda x: -x[1]):
            sat = cs.SAT if (a == "KOSPI" and info["sat_on"]) or (a == "SHY" and not info["sat_on"]) else 0.0
            targets.append({"code": cs.ETF[a][0], "name": cs.ETF[a][1], "asset": a, "weight": round(tw, 4),
                            "perm": round(half * cs.PERMANENT.get(a, 0), 4),
                            "haa": round(half * info["haa"].get(a, 0), 4), "sat": sat})
        state = {"computed": today, "signal_month": info["signal_month"], "canary": round(float(info["canary"]), 4),
                 "mode": "공격" if info["canary"] > 0 else "방어", "safe": cs.ETF[info["safe"]][1],
                 "satellite_mode": cs.SATELLITE_MODE, "sat_on": bool(info["sat_on"]), "band": cs.BAND,
                 "scores": [{"asset": a, "name": cs.ETF[a][1], "score": round(float(info["score"][a]), 4),
                             "picked": a in info["haa"]} for a in cs.HAA_OFFENSIVE],
                 "targets": targets}
        json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"전략 상태 갱신: 기준월 {state['signal_month']} · {state['mode']}")
    except Exception as e:
        print(f"(전략 상태 갱신 건너뜀: {e})")


def main():
    hold, summary = get_balance()
    snap = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
        "total": summary["총평가금액"],
        "cash": summary["주문가능현금"],
        "pnl": summary["평가손익합계"],
        "ret": summary["총평가금액"] / INIT - 1,
        "holdings": [{"name": h["종목명"], "code": h["종목코드"], "qty": h["보유수량"],
                      "price": h["현재가"], "pnl": h["평가손익"], "rt": h["손익률"],
                      "value": h["평가금액"]} for h in hold],
    }
    os.makedirs(os.path.dirname(HIST), exist_ok=True)
    hist = json.load(open(HIST, encoding="utf-8")) if os.path.exists(HIST) else []
    hist = [x for x in hist if x["date"] != snap["date"]]   # 같은 날은 최신으로 갱신
    hist.append(snap)
    hist.sort(key=lambda x: x["date"])
    json.dump(hist, open(HIST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    save_strategy_state(snap["date"])
    print(f"기록됨: {snap['date']} 총평가 {snap['total']:,}원 "
          f"(누적수익 {snap['ret']:+.2%}, 총 {len(hist)}일치)")


if __name__ == "__main__":
    main()
