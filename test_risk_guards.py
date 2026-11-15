"""
Offline regression test suite for MAPLE-aligned TSX-Trader risk & strategy guards.
Uses synthetic snapshots so zero live network calls or Telegram queue writes occur.
"""

import datetime
import os
import tempfile
import unittest
from zoneinfo import ZoneInfo

import pandas as pd

import market_analyzer
import strategy_engine
import send_interval_scan
import send_eod_summary


ET = ZoneInfo("America/Toronto")


def _make_sd(**overrides):
    base = {
        "Price": 50.0,
        "Open": 49.0,
        "High": 50.5,
        "Low": 48.5,
        "Prev_Close": 49.0,
        "Gap_Pct": 0.0,
        "Pct_From_Low": 3.09,
        "Vol_Ratio": 1.35,
        "Vol_SMA_10": 500000.0,
        "Intraday_Dollar_Vol": 2500000.0,
        "Bar_Date": "2026-11-13",
        "Stale_Intraday": False,
        "EMA_5": 49.8,
        "EMA_9": 49.2,
        "EMA_Crossover": "BULLISH",
        "RSI_7": 55.0,
        "ATR_5": 1.0,
        "ADX_14": 25.0,
        "BB_Lower": 46.0,
        "BB_Mid": 49.0,
        "BB_Upper": 53.0,
    }
    base.update(overrides)
    return base


class TestMapleAlignmentGuards(unittest.TestCase):
    def setUp(self):
        self.cfg = market_analyzer.load_config()
        self.eng = strategy_engine.MapleStrategyEngine(self.cfg)
        self.valid_scan_time = datetime.datetime(2026, 11, 13, 10, 30, tzinfo=ET)
        self.chop_time = datetime.datetime(2026, 11, 13, 9, 40, tzinfo=ET)
        self.midday_time = datetime.datetime(2026, 11, 13, 12, 15, tzinfo=ET)
        self.macro_ok = {"GC=F": True, "CL=F": True, "HG=F": True, "VIX_PANIC": False, "VIX_Level": 16.5, "details": {}}

    def test_config_and_sector_map_parity(self):
        self.assertEqual(len(self.cfg.get("portfolio", [])), 32)
        self.assertEqual(self.eng.commission_cad, 0.0)
        self.assertEqual(self.eng.stagnation_days, 4)
        self.assertEqual(self.eng.max_sector_pct, 0.35)
        self.assertEqual(self.eng.max_position_pct, 0.25)
        self.assertEqual(strategy_engine.get_ticker_sector("CLS.TO", self.eng.sector_map), "Technology")
        self.assertEqual(strategy_engine.get_ticker_sector("CCO.TO", self.eng.sector_map), "Energy & Uranium")
        self.assertEqual(strategy_engine.get_ticker_sector("TECK-B.TO", self.eng.sector_map), "Base Metals & Materials")

    def test_ticker_normalization_and_overlay(self):
        self.assertEqual(market_analyzer.normalize_ticker("ATD"), "ATD.TO")
        self.assertEqual(market_analyzer.normalize_ticker("TECK.B.TO"), "TECK-B.TO")
        self.assertEqual(market_analyzer.normalize_ticker("GC=F"), "GC=F")

        # Overlay fresh 1m bars onto daily DataFrame
        idx = pd.to_datetime(["2026-11-12"]).tz_localize(ET)
        daily = pd.DataFrame(
            {"Open": [10.0], "High": [10.5], "Low": [9.8], "Close": [10.2], "Volume": [100000]},
            index=idx,
        )
        m1_idx = pd.to_datetime(["2026-11-13 09:30", "2026-11-13 10:00"]).tz_localize(ET)
        m1 = pd.DataFrame(
            {"Open": [10.3, 10.4], "High": [10.6, 10.9], "Low": [10.2, 10.3], "Close": [10.4, 10.8], "Volume": [5000, 7000]},
            index=m1_idx,
        )
        out = market_analyzer._overlay_fresh_bar(daily, pd.DataFrame(), m1, today_date=datetime.date(2026, 11, 13))
        self.assertEqual(len(out), 2)
        self.assertAlmostEqual(float(out["Close"].iloc[-1]), 10.8)
        self.assertAlmostEqual(float(out["High"].iloc[-1]), 10.9)
        self.assertEqual(int(out["Volume"].iloc[-1]), 12000)

    def test_overbought_ceiling_and_no_double_bypass(self):
        # Hard RSI > 68.0 block even with huge volume
        md = {"RY.TO": _make_sd(RSI_7=69.5, Vol_Ratio=2.5)}
        res = strategy_engine.evaluate_buy_candidates(
            ["RY.TO"], {}, md, {}, self.macro_ok, {}, cash=5000, total_equity=5000, engine=self.eng, now_et=self.valid_scan_time
        )
        self.assertEqual(len(res["alerts"]), 0)
        self.assertIn("Hard overbought block", res["blocked"]["RY.TO"])

        # Double bypass (weak ADX <= 20 AND RSI > 65) blocked even with Vol_Ratio 1.8x
        md2 = {"RY.TO": _make_sd(ADX_14=18.0, RSI_7=66.5, Vol_Ratio=1.80)}
        res2 = strategy_engine.evaluate_buy_candidates(
            ["RY.TO"], {}, md2, {}, self.macro_ok, {}, cash=5000, total_equity=5000, engine=self.eng, now_et=self.valid_scan_time
        )
        self.assertEqual(len(res2["alerts"]), 0)
        self.assertIn("Double bypass blocked", res2["blocked"]["RY.TO"])

        # Single bypass requires >= 1.50x
        md3 = {"RY.TO": _make_sd(ADX_14=18.0, RSI_7=55.0, Vol_Ratio=1.40)}
        res3 = strategy_engine.evaluate_buy_candidates(
            ["RY.TO"], {}, md3, {}, self.macro_ok, {}, cash=5000, total_equity=5000, engine=self.eng, now_et=self.valid_scan_time
        )
        self.assertEqual(len(res3["alerts"]), 0)

        md4 = {"RY.TO": _make_sd(ADX_14=18.0, RSI_7=55.0, Vol_Ratio=1.55)}
        res4 = strategy_engine.evaluate_buy_candidates(
            ["RY.TO"], {}, md4, {}, self.macro_ok, {}, cash=5000, total_equity=5000, engine=self.eng, now_et=self.valid_scan_time
        )
        self.assertEqual(len(res4["alerts"]), 1)

    def test_low_vol_scaled_and_red_candle_gate(self):
        # 1.05x accepted as Low-Volume Scaled Entry when green candle & ADX/RSI pass
        md = {"RY.TO": _make_sd(Vol_Ratio=1.05, Price=50.5, Open=50.0)}
        res = strategy_engine.evaluate_buy_candidates(
            ["RY.TO"], {}, md, {}, self.macro_ok, {}, cash=5000, total_equity=5000, engine=self.eng, now_et=self.valid_scan_time
        )
        self.assertEqual(len(res["alerts"]), 1)
        self.assertEqual(res["alerts"][0]["strategy"], "LOW_VOL_SCALED")

        # Red candle blocked
        md_red = {"RY.TO": _make_sd(Vol_Ratio=1.6, Price=49.5, Open=50.0)}
        res_red = strategy_engine.evaluate_buy_candidates(
            ["RY.TO"], {}, md_red, {}, self.macro_ok, {}, cash=5000, total_equity=5000, engine=self.eng, now_et=self.valid_scan_time
        )
        self.assertEqual(len(res_red["alerts"]), 0)
        self.assertIn("Red intraday candle", res_red["blocked"]["RY.TO"])

    def test_capitulation_cap_chase_and_vix_panic(self):
        # Valid capitulation: Vol > 1.25, RSI < 35, bounce 2.2%, Price > Open -> max 15% tranche
        md = {"SU.TO": _make_sd(Vol_Ratio=1.5, RSI_7=30.0, Pct_From_Low=2.2, EMA_5=48.0, EMA_9=49.5)}
        res = strategy_engine.evaluate_buy_candidates(
            ["SU.TO"], {}, md, {}, self.macro_ok, {}, cash=5000, total_equity=5000, engine=self.eng, now_et=self.valid_scan_time
        )
        self.assertEqual(len(res["alerts"]), 1)
        self.assertEqual(res["alerts"][0]["strategy"], "CAPITULATION")
        self.assertLessEqual(res["alerts"][0]["tranche_pct"], 0.15)

        # Chasing > 4.5% blocked
        md_chase = {"SU.TO": _make_sd(Vol_Ratio=1.5, RSI_7=30.0, Pct_From_Low=5.0, EMA_5=48.0, EMA_9=49.5)}
        res_chase = strategy_engine.evaluate_buy_candidates(
            ["SU.TO"], {}, md_chase, {}, self.macro_ok, {}, cash=5000, total_equity=5000, engine=self.eng, now_et=self.valid_scan_time
        )
        self.assertEqual(len(res_chase["alerts"]), 0)
        self.assertIn("Chasing capitulation", res_chase["blocked"]["SU.TO"])

        # VIX panic blocks capitulation
        macro_panic = dict(self.macro_ok, VIX_PANIC=True, VIX_Level=28.0)
        res_panic = strategy_engine.evaluate_buy_candidates(
            ["SU.TO"], {}, md, {}, macro_panic, {}, cash=5000, total_equity=5000, engine=self.eng, now_et=self.valid_scan_time
        )
        self.assertEqual(len(res_panic["alerts"]), 0)
        self.assertIn("VIX Panic", res_panic["blocked"]["SU.TO"])

    def test_liquidity_stale_earnings_and_commodity_gates(self):
        md = {
            "THIN.TO": _make_sd(Vol_SMA_10=50000, Intraday_Dollar_Vol=200000),
            "STALE.TO": _make_sd(Stale_Intraday=True),
            "AEM.TO": _make_sd(),
            "TECK-B.TO": _make_sd(),
        }
        cal = {"RY.TO": {"trading_days_to_earnings": 2}}
        md["RY.TO"] = _make_sd()
        macro_red = {"GC=F": False, "CL=F": True, "HG=F": False, "VIX_PANIC": False, "details": {}}

        res = strategy_engine.evaluate_buy_candidates(
            ["THIN.TO", "STALE.TO", "RY.TO", "AEM.TO", "TECK-B.TO"],
            {},
            md,
            cal,
            macro_red,
            {},
            cash=5000,
            total_equity=5000,
            engine=self.eng,
            now_et=self.valid_scan_time,
        )
        self.assertEqual(len(res["alerts"]), 0)
        self.assertIn("Thin liquidity", res["blocked"]["THIN.TO"])
        self.assertIn("Stale intraday", res["blocked"]["STALE.TO"])
        self.assertIn("Earnings in 2td", res["blocked"]["RY.TO"])
        self.assertIn("GC=F (Gold) is red", res["blocked"]["AEM.TO"])
        self.assertIn("HG=F (Copper) is red", res["blocked"]["TECK-B.TO"])

    def test_targets_commission_and_ex_div_stop(self):
        # Wealthsimple zero commission
        tgt, stp, eff_stop = strategy_engine.calculate_targets(100.0, atr_5=1.0, bb_mid=101.0, engine=self.eng, td_to_ex_div=2)
        self.assertEqual(tgt, 102.5)  # +2.5% hurdle beats 101 BB_Mid and 101.5 ATR
        self.assertEqual(eff_stop, 4.0)  # -1% ex-div tightening (5% -> 4%)
        self.assertEqual(stp, 96.0)

        # Commission aware override
        cfg_comm = dict(self.cfg, commission_per_order_cad=5.0)
        eng_comm = strategy_engine.MapleStrategyEngine(cfg_comm)
        tgt_c, _, _ = strategy_engine.calculate_targets(100.0, atr_5=1.0, bb_mid=101.0, engine=eng_comm, estimated_shares=10.0)
        self.assertEqual(tgt_c, 103.5)  # 102.5 + (2 * 5 / 10) = 103.5

    def test_four_tier_ratchet_chop_buffer_and_no_cls_cco_exemption(self):
        # Day-4 stagnation exit applies to CLS.TO and CCO.TO with NO exemption
        positions = {
            "CLS.TO": {"shares": 10.0, "acb": 100.0},
            "CCO.TO": {"shares": 10.0, "acb": 100.0},
            "SHOP.TO": {"shares": 10.0, "acb": 100.0},
            "SU.TO": {"shares": 10.0, "acb": 100.0},
        }
        md = {
            "CLS.TO": _make_sd(Price=97.0, Open=97.5, Prev_Close=98.0, EMA_5=98.0, EMA_9=99.0),
            # Green-Day Rally Deferral: Price > Open and Price >= Prev_Close * 1.01
            "CCO.TO": _make_sd(Price=99.0, Open=97.5, Prev_Close=97.5, EMA_5=99.5, EMA_9=100.0),
            # Tier-4 tight trail (>= +5.0%)
            "SHOP.TO": _make_sd(Price=106.0, Open=104.0, Prev_Close=104.0, BB_Upper=110.0, RSI_7=65.0),
            # Chop buffer test (-5.8% loss during 9:40 AM chop should NOT trigger STOP-LOSS because buffer allows -7%)
            "SU.TO": _make_sd(Price=94.2, Open=94.0, Prev_Close=95.0, EMA_5=96.0, EMA_9=95.0),
        }
        cycle_info = {
            "cycles": {
                "CLS.TO": {"days_held": 4, "buy_count": 1},
                "CCO.TO": {"days_held": 5, "buy_count": 1},
                "SHOP.TO": {"days_held": 2, "buy_count": 1},
                "SU.TO": {"days_held": 1, "buy_count": 1},
            }
        }
        res_chop = strategy_engine.evaluate_portfolio_holdings(
            positions, md, {}, cycle_info, engine=self.eng, cash=1000.0, now_et=self.chop_time
        )
        by_t = {h["ticker"]: h for h in res_chop["holdings"]}
        self.assertEqual(by_t["CLS.TO"]["action"], "SELL (STAGNATION)")
        self.assertEqual(by_t["CCO.TO"]["action"], "HOLD")
        self.assertTrue(any("Stagnation Deferred" in f for f in by_t["CCO.TO"]["flags"]))
        self.assertIn("Tier-4 Tight Trail", by_t["SHOP.TO"]["ratchet_advice"])
        self.assertEqual(by_t["SU.TO"]["action"], "HOLD")
        self.assertTrue(any("CHOP BUFFER ACTIVE" in f for f in by_t["SU.TO"]["flags"]))

        # Outside chop (10:30 AM), -5.8% triggers hard stop immediately
        res_reg = strategy_engine.evaluate_portfolio_holdings(
            positions, md, {}, cycle_info, engine=self.eng, cash=1000.0, now_et=self.valid_scan_time
        )
        by_t_reg = {h["ticker"]: h for h in res_reg["holdings"]}
        self.assertEqual(by_t_reg["SU.TO"]["action"], "SELL (STOP-LOSS)")

    def test_cooldown_and_scale_in_rules_plus_time_windows(self):
        # Time blocks
        md = {"RY.TO": _make_sd()}
        self.assertIsNotNone(
            strategy_engine.evaluate_buy_candidates(["RY.TO"], {}, md, {}, self.macro_ok, {}, 5000, 5000, engine=self.eng, now_et=self.chop_time)["window_block"]
        )
        self.assertIsNotNone(
            strategy_engine.evaluate_buy_candidates(["RY.TO"], {}, md, {}, self.macro_ok, {}, 5000, 5000, engine=self.eng, now_et=self.midday_time)["window_block"]
        )

        # 4h post-stop cooldown via cycle dataframe
        trades = pd.DataFrame([
            {"Date": "2026-11-12 10:00:00", "Ticker": "RY.TO", "Action": "BUY", "Quantity": 10, "Price": 100.0, "Amount": -1000.0},
            {"Date": "2026-11-13 09:35:00", "Ticker": "RY.TO", "Action": "SELL", "Quantity": 10, "Price": 94.0, "Amount": 940.0},
        ])
        cyc = strategy_engine.get_cycle_info(trades, now_et=self.valid_scan_time)
        res_cd = strategy_engine.evaluate_buy_candidates(
            ["RY.TO"], {}, md, {}, self.macro_ok, cyc, cash=5000, total_equity=5000, engine=self.eng, now_et=self.valid_scan_time
        )
        self.assertIn("Post-stop cooldown", res_cd["blocked"]["RY.TO"])

        # Scale-In #2 allowed after >= 4h, >= +0.5% above prior buy, >= +1% unrealized gain
        cyc_scale = {
            "cycles": {
                "SHOP.TO": {
                    "days_held": 1,
                    "buy_count": 1,
                    "last_buy_dt": datetime.datetime(2026, 11, 12, 11, 0, tzinfo=ET),
                    "last_buy_price": 49.0,
                }
            }
        }
        positions = {"SHOP.TO": {"shares": 10.0, "acb": 49.0}}
        md_scale = {"SHOP.TO": _make_sd(Price=50.5, Open=49.8)}
        res_scale = strategy_engine.evaluate_buy_candidates(
            ["SHOP.TO"], positions, md_scale, {}, self.macro_ok, cyc_scale, cash=5000, total_equity=5505, engine=self.eng, now_et=self.valid_scan_time
        )
        self.assertEqual(len(res_scale["alerts"]), 1)
        self.assertTrue(res_scale["alerts"][0]["is_scale_in"])

    def test_dossier_interval_and_eod_message_builders(self):
        snap = {
            "config": self.cfg,
            "mode": "SHORT",
            "balances": {"positions": {"CLS.TO": {"shares": 10.0, "acb": 50.0}}, "cash": 4500.0},
            "tickers": ["CLS.TO", "RY.TO", "SU.TO"],
            "cal_map": {"RY.TO": {"trading_days_to_earnings": 1, "earnings_date": "2026-11-16"}},
            "market_data": {
                "CLS.TO": _make_sd(Price=52.0, Prev_Close=50.0, Open=50.2),
                "RY.TO": _make_sd(Price=140.0, Prev_Close=135.0, Open=136.0),
                "SU.TO": _make_sd(Price=55.0, Prev_Close=55.0, Open=54.5),
            },
            "macro_state": self.macro_ok,
        }
        cycle_info = {
            "cycles": {"CLS.TO": {"days_held": 1, "buy_count": 1}},
            "realized_summary": {"total_deposits": 0.0, "total_dividends": 10.0, "cum_realized_pnl": 100.0, "today_closed": []},
        }

        scan_msg = send_interval_scan.build_interval_scan_message(snap, cycle_info, engine=self.eng, now_et=self.valid_scan_time)
        self.assertIn("TOTAL UNREALIZED P&L:", scan_msg)
        self.assertIn("BUY ALERTS (2):", scan_msg)
        self.assertIn("Scale-In #2", scan_msg)
        self.assertIn("SU.TO", scan_msg)

        with tempfile.TemporaryDirectory() as tmpd:
            nav_path = os.path.join(tmpd, "daily_nav.json")
            eod_msg = send_eod_summary.build_eod_summary_message(
                snap, cycle_info, engine=self.eng, now_et=self.valid_scan_time, nav_file=nav_path
            )
            self.assertTrue(os.path.exists(nav_path))
            self.assertIn("Universe Eq-Wt:", eod_msg)
            self.assertIn("SECTOR EXPOSURE (Cap 35%):", eod_msg)
            self.assertIn("DAILY MOVERS ATTRIBUTION", eod_msg)
            self.assertIn("Filtered: Earnings in 1td", eod_msg)


if __name__ == "__main__":
    unittest.main()
