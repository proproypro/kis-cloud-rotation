"""포트폴리오 스냅샷 기록기 — 매일 계좌 상태를 history에 저장(자산곡선용)."""
import json
import os
from datetime import datetime

from kis_balance import get_balance

HIST = os.path.join(os.path.dirname(__file__), "data", "portfolio_history.json")
INIT = 100_000_000


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
    print(f"기록됨: {snap['date']} 총평가 {snap['total']:,}원 "
          f"(누적수익 {snap['ret']:+.2%}, 총 {len(hist)}일치)")


if __name__ == "__main__":
    main()
