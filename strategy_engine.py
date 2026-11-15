"""
Unified MAPLE-aligned strategy engine for TSX-Trader.

Shared across market_analyzer.py, send_interval_scan.py, and send_eod_summary.py
so interval scans, EOD attribution, and risk management follow identical rules.
"""

import datetime
import os
import numpy as np
import pandas as pd

import market_analyzer


GOLD_TICKERS = {"AEM.TO", "ABX.TO", "K.TO", "FNV.TO", "WPM.TO", "PAAS.TO", "AGI.TO"}
OIL_TICKERS = {"CNQ.TO", "SU.TO", "CVE.TO", "TOU.TO", "IMO.TO"}
COPPER_TICKERS = {"TECK-B.TO"}


def get_ticker_sector(ticker, sector_map=None):
    """Maps a TSX ticker to its configured sector (or 'Other')."""
    sym = market_analyzer.normalize_ticker(ticker)
    smap = sector_map if isinstance(sector_map, dict) else {}
    return smap.get(sym, "Other")


class MapleStrategyEngine:
    """Holds MAPLE-aligned thresholds loaded from config.json."""

    def __init__(self, config=None):
        cfg = config if config is not None else market_analyzer.load_config()
        self.config = cfg or {}
        sp = self.config.get("sizing_parameters", {})

        self.min_tranche_pct = float(sp.get("min_tranche_pct", 0.15))
        self.base_tranche_pct = float(sp.get("base_tranche_pct", 0.25))
        self.max_tranche_pct = float(sp.get("max_tranche_pct", 0.35))
        self.cap_max_tranche_pct = float(sp.get("capitulation_max_tranche_pct", 0.15))

        self.vol_cap_ratio = float(sp.get("volume_capitulation_ratio", 1.25))
        self.cap_min_bounce_pct = float(sp.get("capitulation_min_bounce_pct", 1.50))
        self.cap_max_bounce_pct = float(sp.get("capitulation_max_bounce_pct", 4.50))

        self.min_scaled_vol_ratio = float(sp.get("min_scaled_vol_ratio", 1.00))
        self.vol_single_bypass_ratio = float(sp.get("volume_single_bypass_ratio", 1.50))
        self.vol_boost_ratio = float(sp.get("volume_boost_ratio", sp.get("volume_boost_threshold", 1.60)))

        self.min_liquid_vol_sma10 = float(sp.get("min_liquid_vol_sma10", 150000.0))
        self.min_surge_dollar_vol = float(sp.get("min_surge_dollar_vol_cad", 1000000.0))

        self.adx_threshold = float(sp.get("adx_trend_threshold", 20.0))
        self.adx_strong_threshold = float(sp.get("adx_strong_threshold", sp.get("adx_strong_trend", 28.0)))

        self.rsi_oversold_max = float(sp.get("rsi_oversold_max", 35.0))
        self.rsi_sweet_low = float(sp.get("rsi_sweetspot_low", 40.0))
        self.rsi_sweet_high = float(sp.get("rsi_sweetspot_high", 62.0))
        self.rsi_standard_max = float(sp.get("rsi_standard_max", 65.0))
        self.rsi_overbought_limit = float(sp.get("rsi_overbought_limit", 68.0))
        self.max_ema5_extension_pct = float(sp.get("max_ema5_extension_pct", 3.0))

        self.half_risk_trigger_pct = float(sp.get("half_risk_trigger_pct", 2.0))
        self.breakeven_trigger_pct = float(sp.get("breakeven_trigger_pct", 2.5))
        self.profit_trail_trigger_pct = float(sp.get("profit_trail_trigger_pct", 3.5))
        self.profit_trail_stop_pct = float(sp.get("profit_trail_stop_pct", 1.5))
        self.tight_trail_trigger_pct = float(sp.get("tight_trail_trigger_pct", 5.0))
        self.tight_trail_stop_pct = float(sp.get("tight_trail_stop_pct", 3.0))

        self.stop_loss_pct = float(self.config.get("short_term_stop_loss_pct", 5.0))
        self.stagnation_days = int(self.config.get("stagnation_days", 4))
        self.min_net_profit_pct = float(self.config.get("min_net_profit_pct", 2.5))
        self.commission_cad = float(self.config.get("commission_per_order_cad", 0.0))
        self.cooldown_hours = float(self.config.get("scale_in_cooldown_hours", 4.0))
        self.max_position_pct = float(self.config.get("max_position_pct", 0.25))
        self.max_sector_pct = float(self.config.get("max_sector_pct", 0.35))
        self.chop_stop_buffer_pct = float(self.config.get("chop_stop_buffer_pct", 2.0))
        self.sector_map = self.config.get("sector_map", {})


def is_opening_chop(now_et=None):
    """True during Opening Chop (09:30 - 09:59:59 ET)."""
    now = now_et or market_analyzer._now_et()
    mins = now.hour * 60 + now.minute
    return 9 * 60 + 30 <= mins < 10 * 60


def is_midday_fakeout(now_et=None):
    """True during Midday Fake-Out (11:30 - 13:59:59 ET)."""
    now = now_et or market_analyzer._now_et()
    mins = now.hour * 60 + now.minute
    return 11 * 60 + 30 <= mins < 14 * 60


def is_macro_aligned(ticker, macro_state, strategy_type):
    """
    Verifies underlying commodity alignment (GC=F, CL=F, HG=F) and ^VIX panic gate.
    Returns (bool, reason_str).
    """
    sym = market_analyzer.normalize_ticker(ticker)
    state = macro_state or {}

    if strategy_type == "CAPITULATION" and state.get("VIX_PANIC", False):
        vix_lvl = state.get("VIX_Level", "High")
        return False, f"VIX Panic ({vix_lvl}) suppresses falling-knife capitulation"

    if sym in GOLD_TICKERS and not state.get("GC=F", True):
        return False, "GC=F (Gold) is red today"
    if sym in OIL_TICKERS and not state.get("CL=F", True):
        return False, "CL=F (Oil) is red today"
    if sym in COPPER_TICKERS and not state.get("HG=F", True):
        return False, "HG=F (Copper) is red today"
    return True, "Macro aligned"


def calculate_tranche_size(vol_ratio, rsi_7, adx_14, ema_5, ema_9, strategy_type, engine=None):
    """Computes dynamic tranche allocation [0.15 .. 0.35], capped at 0.15 for CAPITULATION."""
    eng = engine or MapleStrategyEngine()
    tranche = eng.base_tranche_pct
    reasons = ["Base 25%"]

    if vol_ratio >= eng.vol_boost_ratio:
        tranche += 0.05
        reasons.append(f"+5% Vol({vol_ratio:.2f}x)")
    elif strategy_type != "CAPITULATION" and vol_ratio < eng.vol_cap_ratio:
        tranche -= 0.05
        reasons.append(f"-5% LowVol({vol_ratio:.2f}x)")

    if strategy_type != "CAPITULATION":
        if eng.rsi_sweet_low <= rsi_7 <= eng.rsi_sweet_high:
            tranche += 0.05
            reasons.append(f"+5% RSI({rsi_7:.1f})")
        elif rsi_7 > eng.rsi_standard_max:
            tranche -= 0.05
            reasons.append(f"-5% HotRSI({rsi_7:.1f})")

    if adx_14 > eng.adx_strong_threshold:
        tranche += 0.05
        reasons.append(f"+5% StrongADX({adx_14:.1f})")

    if ema_9 > 0 and strategy_type != "CAPITULATION":
        ext_pct = ((ema_5 - ema_9) / ema_9) * 100.0
        if ext_pct > 1.5:
            tranche -= 0.05
            reasons.append(f"-5% StretchedEMA({ext_pct:.1f}%)")

    if strategy_type == "CAPITULATION":
        tranche = min(tranche, eng.cap_max_tranche_pct)
        reasons.append(f"CapMax({int(eng.cap_max_tranche_pct * 100)}%)")

    tranche = max(eng.min_tranche_pct, min(eng.max_tranche_pct, round(tranche, 4)))
    return tranche, reasons


def calculate_targets(price, atr_5, bb_mid, engine=None, estimated_shares=100.0, td_to_ex_div=None):
    """
    Calculates commission-aware profit target (>= +2.5% net) and ex-dividend-aware stop loss.
    Returns (target_price, stop_price, effective_stop_pct).
    """
    eng = engine or MapleStrategyEngine()
    eff_stop_pct = eng.stop_loss_pct
    if td_to_ex_div is not None and 0 <= td_to_ex_div <= 3:
        eff_stop_pct = max(eff_stop_pct - 1.0, 1.0)

    stop_price = round(price * (1.0 - eff_stop_pct / 100.0), 2)

    fee_per_share = (2.0 * eng.commission_cad / max(float(estimated_shares), 1.0)) if eng.commission_cad > 0 else 0.0
    min_hurdle = price * (1.0 + eng.min_net_profit_pct / 100.0) + fee_per_share
    atr_target = price + (1.5 * atr_5) if atr_5 > 0 else min_hurdle
    bb_candidate = bb_mid if (bb_mid > 0 and bb_mid >= min_hurdle) else 0.0
    target_price = round(max(bb_candidate, atr_target, min_hurdle), 2)
    return target_price, stop_price, eff_stop_pct


def load_trades_df(trades_file=None):
    """Loads trades.csv safely, parsing timestamps and normalizing tickers."""
    path = trades_file or getattr(market_analyzer, "TRADES_FILE", "trades.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    if df.empty or "Ticker" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["Ticker"] = df["Ticker"].astype(str).apply(market_analyzer.normalize_ticker)
    df["parsed_dt"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


def _row_cash_amount(row):
    """Extracts net cash amount column consistently across Amount / Total_Value."""
    val = row.get("Amount", np.nan)
    if pd.isna(val):
        val = row.get("Total_Value", 0.0)
    return float(val) if not pd.isna(val) else 0.0


def get_cycle_info(trades_df=None, now_et=None):
    """
    Reconstructs active cycle state per ticker from trades.csv:
    - days_held (trading weekdays from cycle_start_dt to today ET)
    - buy_count (buys since last full exit)
    - last_buy_dt, last_buy_price
    - last_loss_exit_dt
    - realized_summary: {total_deposits, total_dividends, cum_realized_pnl, today_closed}
    """
    now = now_et or market_analyzer._now_et()
    today_date = now.date()
    today_str = now.strftime("%Y-%m-%d")

    df = trades_df if trades_df is not None else load_trades_df()
    if df is None or df.empty:
        return {"cycles": {}, "realized_summary": {"total_deposits": 0.0, "total_dividends": 0.0, "cum_realized_pnl": 0.0, "today_closed": []}}

    cycles = {}
    pos_tracker = {}
    total_deposits = 0.0
    total_dividends = 0.0
    cum_realized = 0.0
    today_closed = []

    for _, row in df.iterrows():
        t = market_analyzer.normalize_ticker(str(row.get("Ticker", "")))
        action = str(row.get("Action", "")).upper().strip()
        qty = float(row.get("Quantity", 0) or 0)
        price = float(row.get("Price", 0) or 0)
        dt_val = row.get("parsed_dt")
        if pd.isna(dt_val):
            dt_val = pd.to_datetime(row.get("Date"), errors="coerce")
        dt_obj = dt_val.to_pydatetime() if pd.notna(dt_val) else None
        date_only_str = dt_obj.strftime("%Y-%m-%d") if dt_obj else str(row.get("Date", ""))[:10]
        amt = _row_cash_amount(row)

        if t == "CAD" and action == "DEPOSIT":
            if date_only_str >= "2026-06-22":
                total_deposits += amt
            continue
        if action == "DIVIDEND":
            if date_only_str >= "2026-06-22":
                total_dividends += amt
            continue
        if t in ("CAD", "CASH", "NAN", "") or action == "INIT":
            continue

        state = pos_tracker.setdefault(
            t,
            {
                "shares": 0.0,
                "cost": 0.0,
                "cycle_start_dt": None,
                "buy_count": 0,
                "last_buy_dt": None,
                "last_buy_price": 0.0,
                "last_loss_exit_dt": None,
            },
        )

        if action == "BUY":
            if state["shares"] <= 1e-6:
                state["cycle_start_dt"] = dt_obj
                state["buy_count"] = 0
                state["cost"] = 0.0
                state["shares"] = 0.0
            state["shares"] += qty
            state["cost"] += qty * price
            state["buy_count"] += 1
            state["last_buy_dt"] = dt_obj
            state["last_buy_price"] = price
        elif action == "SELL" and qty > 0:
            avg_cost = (state["cost"] / state["shares"]) if state["shares"] > 1e-6 else price
            realized = (price - avg_cost) * qty
            if date_only_str >= "2026-06-22":
                cum_realized += realized
            if date_only_str == today_str:
                pnl_pct = ((price - avg_cost) / avg_cost * 100.0) if avg_cost > 0 else 0.0
                today_closed.append({"ticker": t, "qty": qty, "price": price, "acb": avg_cost, "pnl_val": realized, "pnl_pct": pnl_pct})

            state["shares"] = max(0.0, state["shares"] - qty)
            state["cost"] = state["shares"] * avg_cost
            if realized < 0 and dt_obj is not None:
                state["last_loss_exit_dt"] = dt_obj
            if state["shares"] <= 1e-6:
                state["shares"] = 0.0
                state["cost"] = 0.0
                state["cycle_start_dt"] = None
                state["buy_count"] = 0

    for t, st in pos_tracker.items():
        days_held = 0
        if st["shares"] > 1e-6 and st["cycle_start_dt"] is not None:
            days_held = max(0, int(np.busday_count(st["cycle_start_dt"].date(), today_date)))
        cycles[t] = {
            "shares": st["shares"],
            "days_held": days_held,
            "buy_count": st["buy_count"],
            "last_buy_dt": st["last_buy_dt"],
            "last_buy_price": st["last_buy_price"],
            "last_loss_exit_dt": st["last_loss_exit_dt"],
            "cycle_start_dt": st["cycle_start_dt"],
        }

    return {
        "cycles": cycles,
        "realized_summary": {
            "total_deposits": total_deposits,
            "total_dividends": total_dividends,
            "cum_realized_pnl": cum_realized,
            "today_closed": today_closed,
        },
    }


def _hours_since(dt_obj, now_et):
    """Returns elapsed hours between a naive/aware trade datetime and now_et."""
    if dt_obj is None:
        return 9999.0
    tz = now_et.tzinfo
    if dt_obj.tzinfo is None and tz is not None:
        dt_aware = dt_obj.replace(tzinfo=tz)
    else:
        dt_aware = dt_obj
    return max(0.0, (now_et - dt_aware).total_seconds() / 3600.0)


def evaluate_portfolio_holdings(positions, market_data, cal_map, cycle_info, engine=None, cash=0.0, now_et=None):
    """
    Evaluates all open positions uniformly (no ticker exemptions) for:
    - Hard stop-loss (ex-dividend & opening chop buffer aware)
    - 4-tier stop ratchet profit protection
    - Upper Bollinger + RSI > 70 profit trim
    - Day-4 stagnation exit & green-day rally deferral / Day-3 approaching warning
    - Sector weight concentrations against 35% portfolio equity cap
    """
    eng = engine or MapleStrategyEngine()
    now = now_et or market_analyzer._now_et()
    in_chop = is_opening_chop(now)
    cycles = (cycle_info or {}).get("cycles", {})

    holdings = []
    sector_values = {}
    total_market_value = 0.0
    total_unrealized_pnl = 0.0
    total_day_pnl = 0.0

    for raw_t, pos in (positions or {}).items():
        shares = float(pos.get("shares", 0) or 0)
        if shares <= 1e-6:
            continue
        t = market_analyzer.normalize_ticker(raw_t)
        acb = float(pos.get("acb", 0) or 0)
        sd = (market_data or {}).get(t) or {}
        price = float(sd.get("Price", acb) or acb)
        prev_close = float(sd.get("Prev_Close", price) or price)
        day_open = float(sd.get("Open", price) or price)
        ema_5 = float(sd.get("EMA_5", 0) or 0)
        ema_9 = float(sd.get("EMA_9", 0) or 0)
        rsi_7 = float(sd.get("RSI_7", 50) or 50)
        bb_upper = float(sd.get("BB_Upper", 0) or 0)

        mkt_val = shares * price
        pnl_val = (price - acb) * shares
        pnl_pct = ((price - acb) / acb * 100.0) if acb > 0 else 0.0
        day_chg_pct = ((price - prev_close) / prev_close * 100.0) if prev_close > 0 else 0.0
        day_pnl = (price - prev_close) * shares

        total_market_value += mkt_val
        total_unrealized_pnl += pnl_val
        total_day_pnl += day_pnl

        sector = get_ticker_sector(t, eng.sector_map)
        sector_values[sector] = sector_values.get(sector, 0.0) + mkt_val

        cal = (cal_map or {}).get(t, {})
        td_ex = cal.get("trading_days_to_ex_dividend")
        eff_stop_pct = eng.stop_loss_pct
        ex_div_warning = False
        if td_ex is not None and 0 <= td_ex <= 3:
            eff_stop_pct = max(eff_stop_pct - 1.0, 1.0)
            ex_div_warning = True

        stop_trigger_pct = eff_stop_pct + (eng.chop_stop_buffer_pct if in_chop else 0.0)
        stop_price = acb * (1.0 - eff_stop_pct / 100.0)
        buffer_to_stop_pct = ((price - stop_price) / price * 100.0) if price > 0 else 0.0

        cyc = cycles.get(t, {})
        days_held = int(cyc.get("days_held", 0))
        buy_count = int(cyc.get("buy_count", 1))

        flags = []
        action = "HOLD"

        if pnl_pct <= -stop_trigger_pct:
            action = "SELL (STOP-LOSS)"
            flags.append(f"HARD STOP: Down {abs(pnl_pct):.2f}% >= {stop_trigger_pct:.1f}% threshold")
        elif in_chop and pnl_pct <= -eff_stop_pct:
            flags.append(f"CHOP BUFFER ACTIVE ({pnl_pct:+.2f}%): Holding through 9:30-10:00 AM unless <= -{stop_trigger_pct:.1f}%")

        # 4-tier stop ratchet
        ratchet_advice = None
        if pnl_pct >= eng.tight_trail_trigger_pct:
            trail_p = acb * (1.0 + eng.tight_trail_stop_pct / 100.0)
            ratchet_advice = f"Tier-4 Tight Trail: Set stop at +{eng.tight_trail_stop_pct:.1f}% (${trail_p:.2f})"
        elif pnl_pct >= eng.profit_trail_trigger_pct:
            trail_p = acb * (1.0 + eng.profit_trail_stop_pct / 100.0)
            ratchet_advice = f"Tier-3 Profit Trail: Set stop at +{eng.profit_trail_stop_pct:.1f}% (${trail_p:.2f})"
        elif pnl_pct >= eng.breakeven_trigger_pct:
            ratchet_advice = f"Tier-2 Breakeven: Move stop to entry (${acb:.2f})"
        elif pnl_pct >= eng.half_risk_trigger_pct:
            half_p = acb * (1.0 - (eff_stop_pct / 2.0) / 100.0)
            ratchet_advice = f"Tier-1 Half-Risk: Tighten stop to -{eff_stop_pct / 2.0:.1f}% (${half_p:.2f})"
        if ratchet_advice:
            flags.append(ratchet_advice)

        if bb_upper > 0 and price >= bb_upper and rsi_7 > 70.0:
            if action == "HOLD":
                action = "TRIM (OVERBOUGHT)"
            flags.append(f"Profit Trim: Hit Upper BB (${bb_upper:.2f}) & RSI {rsi_7:.1f} > 70")

        # Day-4 stagnation exit & Day-3 approaching warning (uniform across all tickers)
        if days_held >= eng.stagnation_days and pnl_pct < 0 and ema_5 > 0 and ema_9 > 0:
            if price < min(ema_5, ema_9):
                is_green_rally = (price > day_open) and (prev_close > 0 and price >= prev_close * 1.01)
                if is_green_rally:
                    flags.append(f"Stagnation Deferred (Day {days_held}): Intraday rally +{day_chg_pct:.2f}% (Green Candle)")
                else:
                    if action == "HOLD":
                        action = "SELL (STAGNATION)"
                    flags.append(f"Day-{days_held} Stagnation Exit: Negative ({pnl_pct:+.2f}%) & Price < min(EMA5, EMA9)")
            elif ema_5 > ema_9:
                flags.append(f"Day-{days_held} Watch: Negative ({pnl_pct:+.2f}%) but EMA5 > EMA9 intact")
        elif days_held == eng.stagnation_days - 1 and pnl_pct < 0:
            flags.append(f"Approaching Day-{eng.stagnation_days} Stagnation Exit tomorrow if < min(EMA5, EMA9)")

        if ex_div_warning:
            flags.append(f"Ex-Div in {td_ex}td: Stop tightened to -{eff_stop_pct:.1f}%")

        holdings.append({
            "ticker": t,
            "sector": sector,
            "shares": shares,
            "acb": acb,
            "price": price,
            "prev_close": prev_close,
            "mkt_val": mkt_val,
            "pnl_val": pnl_val,
            "pnl_pct": pnl_pct,
            "day_chg_pct": day_chg_pct,
            "day_pnl": day_pnl,
            "days_held": days_held,
            "buy_count": buy_count,
            "eff_stop_pct": eff_stop_pct,
            "stop_price": round(stop_price, 2),
            "buffer_to_stop_pct": round(buffer_to_stop_pct, 2),
            "ratchet_advice": ratchet_advice,
            "action": action,
            "flags": flags,
            "ema_bullish": bool(ema_5 > ema_9 and ema_5 > 0),
            "rsi_7": rsi_7,
        })

    total_equity = cash + total_market_value
    sector_weights = {}
    sector_warnings = []
    for sec, val in sorted(sector_values.items(), key=lambda x: x[1], reverse=True):
        pct = (val / total_equity) if total_equity > 0 else 0.0
        sector_weights[sec] = {"value": val, "pct": pct}
        if pct > eng.max_sector_pct:
            sector_warnings.append(f"{sec}: {pct * 100:.1f}% exceeds {eng.max_sector_pct * 100:.0f}% sector cap")

    return {
        "holdings": holdings,
        "total_market_value": total_market_value,
        "total_equity": total_equity,
        "total_unrealized_pnl": total_unrealized_pnl,
        "total_day_pnl": total_day_pnl,
        "sector_weights": sector_weights,
        "sector_warnings": sector_warnings,
    }


def _check_liquidity_and_calendar(sd, cal, eng):
    """Shared liquidity, stale bar, and earnings gate check. Returns block reason or None."""
    if not isinstance(sd, dict):
        return "Missing market data"
    if sd.get("Stale_Intraday"):
        return f"Stale intraday bar ({sd.get('Bar_Date', 'N/A')})"

    td_earn = cal.get("trading_days_to_earnings") if cal else None
    if td_earn is None and cal:
        td_earn = cal.get("days_to_earnings")
    if td_earn is not None and 0 <= td_earn <= 3:
        return f"Earnings in {td_earn}td ({cal.get('earnings_date', 'N/A')})"

    vol_sma10 = float(sd.get("Vol_SMA_10", 0) or 0)
    dollar_vol = float(sd.get("Intraday_Dollar_Vol", 0) or 0)
    if vol_sma10 > 0 and vol_sma10 < eng.min_liquid_vol_sma10 and dollar_vol < eng.min_surge_dollar_vol:
        return f"Thin liquidity (10d AvgVol {vol_sma10:,.0f} < {eng.min_liquid_vol_sma10:,.0f})"
    return None


def _evaluate_entry_signal(t, sd, cal, macro_state, eng):
    """Evaluates whether a ticker satisfies CAPITULATION, BREAKOUT, or LOW_VOL_SCALED entry rules."""
    block = _check_liquidity_and_calendar(sd, cal, eng)
    if block:
        return None, block

    price = float(sd.get("Price", 0) or 0)
    day_open = float(sd.get("Open", 0) or 0)
    vol_ratio = float(sd.get("Vol_Ratio", 0) or 0)
    ema_5 = float(sd.get("EMA_5", 0) or 0)
    ema_9 = float(sd.get("EMA_9", 0) or 0)
    rsi_7 = float(sd.get("RSI_7", 50) or 50)
    adx_14 = float(sd.get("ADX_14", 0) or 0)
    pct_from_low = float(sd.get("Pct_From_Low", 0) or 0)

    if price <= 0 or day_open <= 0:
        return None, "Invalid price/open"
    if price <= day_open:
        return None, "Red intraday candle (Price <= Open)"

    # 1. Capitulation Reversal
    if vol_ratio > eng.vol_cap_ratio and rsi_7 < eng.rsi_oversold_max:
        if pct_from_low < eng.cap_min_bounce_pct:
            return None, f"Knife-catch guard (+{pct_from_low:.2f}% < +{eng.cap_min_bounce_pct:.2f}% from Low)"
        if pct_from_low > eng.cap_max_bounce_pct:
            return None, f"Chasing capitulation (+{pct_from_low:.2f}% > +{eng.cap_max_bounce_pct:.2f}% from Low)"
        aligned, m_reason = is_macro_aligned(t, macro_state, "CAPITULATION")
        if not aligned:
            return None, m_reason
        return {"strategy": "CAPITULATION", "label": "Capitulation Reversal"}, None

    # 2. Momentum Breakout / Low-Volume Scaled Entry
    if ema_5 <= ema_9:
        return None, "Bearish EMA alignment (EMA5 <= EMA9)"
    if rsi_7 > eng.rsi_overbought_limit:
        return None, f"Hard overbought block (RSI {rsi_7:.1f} > {eng.rsi_overbought_limit:.1f})"
    if ema_9 > 0:
        ext_pct = ((ema_5 - ema_9) / ema_9) * 100.0
        if ext_pct > eng.max_ema5_extension_pct:
            return None, f"EMA5 extended +{ext_pct:.2f}% > {eng.max_ema5_extension_pct:.1f}% above EMA9"
    if vol_ratio < eng.min_scaled_vol_ratio:
        return None, f"Low volume ({vol_ratio:.2f}x < {eng.min_scaled_vol_ratio:.2f}x)"

    weak_adx = adx_14 <= eng.adx_threshold
    hot_rsi = rsi_7 > eng.rsi_standard_max
    if weak_adx and hot_rsi:
        return None, f"Double bypass blocked (ADX {adx_14:.1f} <= {eng.adx_threshold:.0f} AND RSI {rsi_7:.1f} > {eng.rsi_standard_max:.0f})"
    if (weak_adx or hot_rsi) and vol_ratio < eng.vol_single_bypass_ratio:
        which = f"ADX {adx_14:.1f}" if weak_adx else f"RSI {rsi_7:.1f}"
        return None, f"Single bypass needs Vol >= {eng.vol_single_bypass_ratio:.2f}x ({which}, Vol {vol_ratio:.2f}x)"

    aligned, m_reason = is_macro_aligned(t, macro_state, "BREAKOUT")
    if not aligned:
        return None, m_reason

    if vol_ratio >= eng.vol_cap_ratio:
        return {"strategy": "BREAKOUT", "label": "Momentum Breakout"}, None
    return {"strategy": "LOW_VOL_SCALED", "label": "Low-Volume Scaled Entry"}, None


def evaluate_buy_candidates(tickers, positions, market_data, cal_map, macro_state, cycle_info, cash, total_equity, engine=None, sector_weights=None, now_et=None):
    """
    Evaluates all universe tickers for new buys or Scale-In #2 additions, enforcing time windows,
    post-stop cooldowns, technical/macro guards, dynamic tranche sizing, and concentration caps.
    """
    eng = engine or MapleStrategyEngine()
    now = now_et or market_analyzer._now_et()

    if is_opening_chop(now):
        return {"alerts": [], "blocked": {}, "window_block": "Opening Chop Window (09:30-10:00 ET)"}
    if is_midday_fakeout(now):
        return {"alerts": [], "blocked": {}, "window_block": "Midday Fake-Out Window (11:30-14:00 ET)"}

    cycles = (cycle_info or {}).get("cycles", {})
    sec_weights = dict(sector_weights or {})
    alerts = []
    blocked = {}

    for raw_t in tickers:
        t = market_analyzer.normalize_ticker(raw_t)
        sd = (market_data or {}).get(t)
        cal = (cal_map or {}).get(t, {})
        cyc = cycles.get(t, {})
        pos = (positions or {}).get(t, {"shares": 0.0, "acb": 0.0})
        shares = float(pos.get("shares", 0) or 0)
        acb = float(pos.get("acb", 0) or 0)

        # 4h post-stop cooldown
        last_loss_dt = cyc.get("last_loss_exit_dt")
        if last_loss_dt is not None and _hours_since(last_loss_dt, now) < eng.cooldown_hours:
            blocked[t] = f"Post-stop cooldown ({_hours_since(last_loss_dt, now):.1f}h < {eng.cooldown_hours:.0f}h)"
            continue

        sig, reason = _evaluate_entry_signal(t, sd, cal, macro_state, eng)
        if not sig:
            blocked[t] = reason
            continue

        price = float(sd["Price"])
        is_scale_in = shares > 1e-6
        if is_scale_in:
            if cyc.get("buy_count", 1) >= 2:
                blocked[t] = "Scale-In blocked (max 2 buys per cycle reached)"
                continue
            last_buy_dt = cyc.get("last_buy_dt")
            if last_buy_dt is not None and _hours_since(last_buy_dt, now) < eng.cooldown_hours:
                blocked[t] = f"Scale-In cooldown (< {eng.cooldown_hours:.0f}h since last buy)"
                continue
            last_buy_p = float(cyc.get("last_buy_price", acb) or acb)
            if last_buy_p > 0 and price < last_buy_p * 1.005:
                blocked[t] = "Scale-In blocked (Price < +0.5% above prior buy)"
                continue
            if acb > 0 and ((price - acb) / acb * 100.0) < 1.0:
                blocked[t] = "Scale-In blocked (Unrealized gain < +1.0%)"
                continue

        tranche_pct, size_reasons = calculate_tranche_size(
            float(sd.get("Vol_Ratio", 0) or 0),
            float(sd.get("RSI_7", 50) or 50),
            float(sd.get("ADX_14", 0) or 0),
            float(sd.get("EMA_5", 0) or 0),
            float(sd.get("EMA_9", 0) or 0),
            sig["strategy"],
            engine=eng,
        )
        alloc_cad = cash * tranche_pct
        if is_scale_in:
            alloc_cad = min(alloc_cad, cash * 0.5)

        cur_val = shares * price
        max_ticker_headroom = max(0.0, (eng.max_position_pct * total_equity) - cur_val) if total_equity > 0 else alloc_cad
        sector = get_ticker_sector(t, eng.sector_map)
        cur_sec_val = (sec_weights.get(sector, {}) or {}).get("value", 0.0)
        max_sector_headroom = max(0.0, (eng.max_sector_pct * total_equity) - cur_sec_val) if total_equity > 0 else alloc_cad

        capped_alloc = min(alloc_cad, max_ticker_headroom, max_sector_headroom, cash)
        if capped_alloc < 100.0:
            blocked[t] = f"Portfolio/Sector cap or cash headroom too small (${capped_alloc:.0f})"
            continue

        est_shares = capped_alloc / price
        td_ex = cal.get("trading_days_to_ex_dividend")
        target_p, stop_p, eff_stop = calculate_targets(
            price,
            float(sd.get("ATR_5", 0) or 0),
            float(sd.get("BB_Mid", 0) or 0),
            engine=eng,
            estimated_shares=est_shares,
            td_to_ex_div=td_ex,
        )

        # Deterministic strength ranking score
        score = (float(sd.get("Vol_Ratio", 1.0)) * 20.0) + float(sd.get("ADX_14", 0))
        if sig["strategy"] == "CAPITULATION":
            score += 15.0

        alerts.append({
            "ticker": t,
            "sector": sector,
            "strategy": sig["strategy"],
            "label": f"Scale-In #2 ({sig['label']})" if is_scale_in else sig["label"],
            "is_scale_in": is_scale_in,
            "price": price,
            "tranche_pct": tranche_pct,
            "alloc_cad": round(capped_alloc, 2),
            "target_price": target_p,
            "stop_price": stop_p,
            "eff_stop_pct": eff_stop,
            "vol_ratio": float(sd.get("Vol_Ratio", 0) or 0),
            "rsi_7": float(sd.get("RSI_7", 0) or 0),
            "adx_14": float(sd.get("ADX_14", 0) or 0),
            "pct_from_low": float(sd.get("Pct_From_Low", 0) or 0),
            "size_reasons": size_reasons,
            "score": score,
        })

    alerts.sort(key=lambda x: x["score"], reverse=True)
    return {"alerts": alerts, "blocked": blocked, "window_block": None}


def scan_daily_movers(tickers, market_data, cal_map, macro_state, engine=None):
    """
    EOD attribution scanner: identifies significant daily winners (>= +2.0% vs Prev Close
    OR positive day with >= +2.5% rebound from Low) and classifies Actionable vs Filtered.
    """
    eng = engine or MapleStrategyEngine()
    movers = []
    for raw_t in tickers:
        t = market_analyzer.normalize_ticker(raw_t)
        sd = (market_data or {}).get(t)
        if not isinstance(sd, dict):
            continue
        price = float(sd.get("Price", 0) or 0)
        prev_close = float(sd.get("Prev_Close", 0) or 0)
        pct_from_low = float(sd.get("Pct_From_Low", 0) or 0)
        if price <= 0 or prev_close <= 0:
            continue
        day_gain_pct = ((price - prev_close) / prev_close) * 100.0
        if day_gain_pct >= 2.0 or (day_gain_pct > 0 and pct_from_low >= 2.5):
            cal = (cal_map or {}).get(t, {})
            sig, reason = _evaluate_entry_signal(t, sd, cal, macro_state, eng)
            movers.append({
                "ticker": t,
                "day_gain_pct": round(day_gain_pct, 2),
                "pct_from_low": round(pct_from_low, 2),
                "vol_ratio": float(sd.get("Vol_Ratio", 0) or 0),
                "rsi_7": float(sd.get("RSI_7", 0) or 0),
                "actionable": sig is not None,
                "strategy": sig["label"] if sig else "Filtered",
                "filter_reason": None if sig else reason,
            })

    movers.sort(key=lambda x: x["day_gain_pct"], reverse=True)
    return movers
