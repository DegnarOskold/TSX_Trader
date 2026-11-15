"""
End-of-Day Summary for TSX-Trader.

Uses market_analyzer.fetch_universe_snapshot() + strategy_engine.py
to emit a full MAPLE-aligned EOD recap with NAV tracking, 32-stock
equal-weight universe alpha, sector weights, stop buffers, and mover attribution.
"""

import json
import os
import sys

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
DAILY_NAV_FILE = os.path.join(BASE_DIR, "daily_nav.json")


def update_daily_nav_snapshot(date_str, total_equity, cash, market_value, unrealized_pnl, nav_file=DAILY_NAV_FILE):
    """Loads daily_nav.json, computes previous-day comparison, and persists today's snapshot."""
    history = {}
    if os.path.exists(nav_file):
        try:
            with open(nav_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    history = loaded
        except Exception:
            history = {}

    prev_dates = sorted(d for d in history.keys() if d < date_str)
    prev_nav = None
    if prev_dates:
        prev_nav = float(history[prev_dates[-1]].get("total_equity", 0.0) or 0.0)

    history[date_str] = {
        "total_equity": round(total_equity, 2),
        "cash": round(cash, 2),
        "market_value": round(market_value, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
    }
    try:
        with open(nav_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, sort_keys=True)
    except Exception:
        pass
    return prev_nav


def compute_universe_benchmark(tickers, market_data):
    """Computes equal-weight average daily % change across the configured TSX universe."""
    changes = []
    for raw_t in tickers:
        t = market_analyzer.normalize_ticker(raw_t)
        sd = (market_data or {}).get(t)
        if not isinstance(sd, dict):
            continue
        p = float(sd.get("Price", 0) or 0)
        prev = float(sd.get("Prev_Close", 0) or 0)
        if p > 0 and prev > 0:
            changes.append(((p - prev) / prev) * 100.0)
    if not changes:
        return None
    return round(sum(changes) / len(changes), 2)


def build_eod_summary_message(snap, cycle_info, engine=None, now_et=None, nav_file=DAILY_NAV_FILE):
    """Builds the End-of-Day Telegram summary and updates daily NAV snapshot."""
    eng = engine or strategy_engine.MapleStrategyEngine(snap.get("config"))
    now = now_et or market_analyzer._now_et()
    date_str = now.strftime("%Y-%m-%d")

    balances = snap.get("balances", {})
    positions = balances.get("positions", {})
    cash = float(balances.get("cash", 0.0) or 0.0)
    market_data = snap.get("market_data", {})
    cal_map = snap.get("cal_map", {})
    macro_state = snap.get("macro_state", {})
    tickers = snap.get("tickers", [])

    realized_sum = cycle_info.get("realized_summary", {})
    total_deposits = float(realized_sum.get("total_deposits", 0.0) or 0.0)
    total_dividends = float(realized_sum.get("total_dividends", 0.0) or 0.0)
    cum_realized = float(realized_sum.get("cum_realized_pnl", 0.0) or 0.0)
    today_closed = realized_sum.get("today_closed", [])

    port = strategy_engine.evaluate_portfolio_holdings(
        positions, market_data, cal_map, cycle_info, engine=eng, cash=cash, now_et=now
    )
    total_equity = port["total_equity"]
    total_mkt = port["total_market_value"]
    total_unreal = port["total_unrealized_pnl"]
    total_day_pnl = port["total_day_pnl"]

    start_equity = 5920.88 + total_deposits
    total_net_pnl = cum_realized + total_dividends + total_unreal
    net_ret_pct = ((total_equity - start_equity) / start_equity * 100.0) if start_equity > 0 else 0.0

    prev_nav = update_daily_nav_snapshot(date_str, total_equity, cash, total_mkt, total_unreal, nav_file=nav_file)
    base_for_day = prev_nav if (prev_nav and prev_nav > 0) else (total_equity - total_day_pnl)
    port_day_pct = ((total_day_pnl / base_for_day) * 100.0) if base_for_day > 0 else 0.0

    bench_pct = compute_universe_benchmark(tickers, market_data)
    alpha_str = f" | Alpha vs Eq-Wt TSX: {port_day_pct - bench_pct:+.2f}%" if bench_pct is not None else ""
    bench_line = (
        f"Day Change: ${total_day_pnl:+,.2f} ({port_day_pct:+.2f}%) | Universe Eq-Wt: {bench_pct:+.2f}%{alpha_str}"
        if bench_pct is not None
        else f"Day Change: ${total_day_pnl:+,.2f} ({port_day_pct:+.2f}%)"
    )

    lines = [
        f"TSX EOD SUMMARY | {date_str}",
        f"Portfolio NAV: ${total_equity:,.2f} (Cash: ${cash:,.2f} | Invested: ${total_mkt:,.2f})",
        bench_line,
        f"Cumulative P&L (since Jun 22): ${total_net_pnl:+,.2f} ({net_ret_pct:+.2f}% | Realized: ${cum_realized:+,.2f}, Div: ${total_dividends:+,.2f})",
    ]
    if port["holdings"]:
        lines.append(f"TOTAL UNREALIZED P&L: ${total_unreal:+,.2f}")

    # Closed trades today
    if today_closed:
        lines.append("")
        lines.append("CLOSED TRADES TODAY:")
        for tr in today_closed:
            lines.append(
                f"- {tr['ticker']}: Sold {tr['qty']:.4f} @ ${tr['price']:.2f} "
                f"(ACB ${tr['acb']:.2f}) -> ${tr['pnl_val']:+.2f} ({tr['pnl_pct']:+.2f}%)"
            )

    # Open holdings with stop buffers & stagnation flags
    lines.append("")
    if port["holdings"]:
        lines.append("OPEN HOLDINGS & STOP BUFFERS:")
        for h in port["holdings"]:
            action_lbl = f" [{h['action']}]" if h["action"] != "HOLD" else ""
            lines.append(
                f"- {h['ticker']}{action_lbl}: ${h['price']:.2f} ({h['day_chg_pct']:+.2f}% day) | "
                f"P&L {h['pnl_pct']:+.2f}% (${h['pnl_val']:+.2f}) | Day {h['days_held']} | "
                f"Stop ${h['stop_price']:.2f} ({h['buffer_to_stop_pct']:.1f}% buffer)"
            )
            for flag in h["flags"]:
                lines.append(f"  * {flag}")
    else:
        lines.append("OPEN HOLDINGS: None (100% Cash).")

    # Sector exposure breakdown (Cap 35%)
    if port["sector_weights"]:
        lines.append("")
        sec_parts = [f"{sec} {info['pct']*100:.1f}%" for sec, info in port["sector_weights"].items()]
        lines.append(f"SECTOR EXPOSURE (Cap {eng.max_sector_pct*100:.0f}%): " + " | ".join(sec_parts))
        for w in port["sector_warnings"]:
            lines.append(f"  * ALERT: {w}")

    # Macro commodity + VIX wrap
    details = macro_state.get("details", {})
    macro_parts = []
    for sym in ["CL=F", "GC=F", "HG=F", "^VIX"]:
        d = details.get(sym)
        if d:
            if sym == "^VIX":
                macro_parts.append(f"VIX {d['price']:.2f} ({d['chg_pct']:+.2f}%)" + (" PANIC" if d.get("panic") else ""))
            else:
                macro_parts.append(f"{sym} ${d['price']:.2f} ({d['chg_pct']:+.2f}%)")
    if macro_parts:
        lines.append("")
        lines.append("MACRO & COMMODITIES: " + " | ".join(macro_parts))

    # Daily movers attribution (Actionable vs Filtered)
    movers = strategy_engine.scan_daily_movers(tickers, market_data, cal_map, macro_state, engine=eng)
    if movers:
        lines.append("")
        lines.append("DAILY MOVERS ATTRIBUTION (Top 6):")
        for m in movers[:6]:
            tag = m["strategy"] if m["actionable"] else f"Filtered: {m['filter_reason']}"
            lines.append(
                f"- {m['ticker']}: {m['day_gain_pct']:+.2f}% (Low+{m['pct_from_low']:.1f}%, "
                f"Vol {m['vol_ratio']:.2f}x, RSI {m['rsi_7']:.1f}) -> {tag}"
            )

    return "\n".join(lines)


def send_eod():
    now_et = market_analyzer._now_et()
    if now_et.weekday() >= 5:
        print(f"Weekend ({now_et.strftime('%A')}). Skipping TSX EOD summary.")
        return

    snap = market_analyzer.fetch_universe_snapshot()
    trades_df = strategy_engine.load_trades_df()
    cycle_info = strategy_engine.get_cycle_info(trades_df, now_et=now_et)
    engine = strategy_engine.MapleStrategyEngine(snap.get("config"))

    msg = build_eod_summary_message(snap, cycle_info, engine=engine, now_et=now_et)
    print(msg)

    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "5286201039")
    entry = {"chat_id": chat_id, "text": msg}
    with open(QUEUE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"Queued EOD summary ({len(msg)} chars) to {QUEUE_FILE}")


if __name__ == "__main__":
    send_eod()
