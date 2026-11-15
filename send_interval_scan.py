"""
Interval Market Scan for TSX-Trader.

Uses market_analyzer.fetch_universe_snapshot() + strategy_engine.py
to emit clean, MAPLE-aligned Telegram scan alerts to outgoing_queue.jsonl.
"""

import datetime
import json
import os
import sys

# Ensure TSX-Trader directory is on sys.path for both CLI & module imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except Exception:
    pass

import market_analyzer
import strategy_engine


QUEUE_FILE = os.path.join(BASE_DIR, "outgoing_queue.jsonl")


def build_interval_scan_message(snap, cycle_info, engine=None, now_et=None):
    """Builds the formatted interval scan alert text cleanly without side effects."""
    eng = engine or strategy_engine.MapleStrategyEngine(snap.get("config"))
    now = now_et or market_analyzer._now_et()
    balances = snap.get("balances", {})
    positions = balances.get("positions", {})
    cash = float(balances.get("cash", 0.0) or 0.0)
    market_data = snap.get("market_data", {})
    cal_map = snap.get("cal_map", {})
    macro_state = snap.get("macro_state", {})
    tickers = snap.get("tickers", [])

    realized_sum = cycle_info.get("realized_summary", {})
    total_deposits = float(realized_sum.get("total_deposits", 0.0) or 0.0)
    start_equity = 5920.88 + total_deposits

    port = strategy_engine.evaluate_portfolio_holdings(
        positions, market_data, cal_map, cycle_info, engine=eng, cash=cash, now_et=now
    )
    total_equity = port["total_equity"]
    total_unreal = port["total_unrealized_pnl"]
    net_ret_pct = ((total_equity - start_equity) / start_equity * 100.0) if start_equity > 0 else 0.0

    buys = strategy_engine.evaluate_buy_candidates(
        tickers,
        positions,
        market_data,
        cal_map,
        macro_state,
        cycle_info,
        cash=cash,
        total_equity=total_equity,
        engine=eng,
        sector_weights=port["sector_weights"],
        now_et=now,
    )

    lines = [
        f"TSX SCAN | {now.strftime('%Y-%m-%d %H:%M ET')}",
        f"Equity: ${total_equity:,.2f} ({net_ret_pct:+.2f}%) | Cash: ${cash:,.2f}",
    ]
    if port["holdings"]:
        lines.append(f"TOTAL UNREALIZED P&L: ${total_unreal:+,.2f} (Day: ${port['total_day_pnl']:+,.2f})")

    # Macro strip
    details = macro_state.get("details", {})
    macro_bits = []
    for sym in ["CL=F", "GC=F", "HG=F"]:
        d = details.get(sym)
        if d:
            tag = "UP" if d.get("green") else "DN"
            macro_bits.append(f"{sym}:{tag}({d['chg_pct']:+.1f}%)")
    if "^VIX" in details:
        vd = details["^VIX"]
        vix_tag = f" PANIC!" if vd.get("panic") else ""
        macro_bits.append(f"VIX:{vd['price']:.1f}{vix_tag}")
    if macro_bits:
        lines.append("Macro: " + " | ".join(macro_bits))

    # Portfolio holdings & exits / ratchets
    lines.append("")
    if port["holdings"]:
        lines.append("HOLDINGS:")
        for h in port["holdings"]:
            status_tag = f" [{h['action']}]" if h["action"] != "HOLD" else ""
            lines.append(
                f"- {h['ticker']}{status_tag}: ${h['price']:.2f} vs ACB ${h['acb']:.2f} "
                f"({h['pnl_pct']:+.2f}% / ${h['pnl_val']:+.2f}) | Day {h['days_held']} | "
                f"Stop ${h['stop_price']:.2f} ({h['buffer_to_stop_pct']:.1f}% buf)"
            )
            for flag in h["flags"]:
                lines.append(f"  * {flag}")
    else:
        lines.append("HOLDINGS: All cash (0 open positions).")

    if port["sector_warnings"]:
        lines.append("")
        lines.append("SECTOR CAP ALERTS:")
        for w in port["sector_warnings"]:
            lines.append(f"- {w}")

    # Actionable Buy / Scale-In Signals
    lines.append("")
    if buys["window_block"]:
        lines.append(f"BUY SCANNER PAUSED: {buys['window_block']}")
    elif buys["alerts"]:
        lines.append(f"BUY ALERTS ({len(buys['alerts'])}):")
        for a in buys["alerts"]:
            lines.append(
                f"- {a['ticker']} [{a['label']}]: ${a['price']:.2f} | "
                f"Alloc {a['tranche_pct']*100:.0f}% (${a['alloc_cad']:,.2f})"
            )
            lines.append(
                f"  Target: ${a['target_price']:.2f} | Stop: ${a['stop_price']:.2f} (-{a['eff_stop_pct']:.1f}%) | "
                f"Vol {a['vol_ratio']:.2f}x, RSI {a['rsi_7']:.1f}, ADX {a['adx_14']:.1f}, Low+{a['pct_from_low']:.1f}%"
            )
    else:
        lines.append("BUY ALERTS: None passing MAPLE liquidity, technical & macro filters.")

    return "\n".join(lines)


def send_scan():
    now_et = market_analyzer._now_et()
    if now_et.weekday() >= 5:
        print(f"Weekend ({now_et.strftime('%A')}). Skipping TSX interval scan.")
        return
    mins = now_et.hour * 60 + now_et.minute
    if not (565 <= mins <= 965):
        print(f"Outside market hours ({now_et.strftime('%H:%M ET')}). Skipping scan.")
        return

    snap = market_analyzer.fetch_universe_snapshot()
    trades_df = strategy_engine.load_trades_df()
    cycle_info = strategy_engine.get_cycle_info(trades_df, now_et=now_et)
    engine = strategy_engine.MapleStrategyEngine(snap.get("config"))

    msg = build_interval_scan_message(snap, cycle_info, engine=engine, now_et=now_et)
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "5286201039")
    entry = {"chat_id": chat_id, "text": msg}
    with open(QUEUE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"Queued interval scan ({len(msg)} chars) to {QUEUE_FILE}")


if __name__ == "__main__":
    send_scan()
