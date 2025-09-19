"""
Simplified and sanitized GUI replacement (single-file).
Implements the 4-stage workflow: defaults -> GUI -> validate -> runtime (no persistence).
This file standardizes variable names (bt_*, ft_*) and provides explicit mapping helpers.
Extend the mapping in build_runtime_config() as needed for additional config keys.
"""
import copy
import logging
import pytz
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from utils.config_helper import (
    create_config_from_defaults,
    get_logging_verbosity_options,
    validate_config,
    freeze_config,
)
from utils.logger_setup import setup_logging_from_config
from backtest.backtest_runner import BacktestRunner
from live.trader import LiveTrader

logger = logging.getLogger(__name__)


def now_ist():
    return datetime.now(pytz.timezone("Asia/Kolkata"))


class UnifiedTradingGUI(tk.Tk):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Unified Trading System")
        self.geometry("1100x700")

        # === CONFIGURATION WORKFLOW ===
        # 1) Start from defaults (defensive deep copy)
        self.defaults = create_config_from_defaults()
        self.runtime_config = copy.deepcopy(self.defaults)

        # 2) Initialize logger from defaults/runtime (so GUI actions are logged)
        try:
            setup_logging_from_config(self.runtime_config)
        except Exception:
            logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # 3) Create GUI variables (all bt_/ft_ variables should be created here)
        self._initialize_all_variables()

        # 4) Populate GUI variables from runtime_config defaults
        self._initialize_variables_from_runtime_config()

        # 5) Build UI (kept minimal but extendable)
        self._build_ui()

    def _initialize_all_variables(self):
        # Backtest variables
        self.bt_data_path = tk.StringVar(value="")
        self.bt_available_capital = tk.DoubleVar(value=100000.0)
        self.bt_risk_percentage = tk.DoubleVar(value=1.0)
        self.bt_use_vwap = tk.BooleanVar(value=False)
        self.bt_use_ema = tk.BooleanVar(value=True)
        self.bt_fast_ema_period = tk.IntVar(value=12)
        self.bt_slow_ema_period = tk.IntVar(value=26)
        self.bt_use_macd = tk.BooleanVar(value=True)
        self.bt_macd_fast = tk.IntVar(value=12)
        self.bt_macd_slow = tk.IntVar(value=26)
        self.bt_macd_signal = tk.IntVar(value=9)
        self.bt_tp1_points = tk.DoubleVar(value=50.0)
        self.bt_tp2_points = tk.DoubleVar(value=100.0)
        self.bt_tp3_points = tk.DoubleVar(value=0.0)
        self.bt_sl_points = tk.DoubleVar(value=100.0)
        self.bt_start_date = tk.StringVar(value="")
        self.bt_end_date = tk.StringVar(value="")

        # Forward-test / Live-trade variables (ft_)
        self.ft_account = tk.StringVar(value="")
        self.ft_trade_size = tk.DoubleVar(value=1.0)
        self.ft_enable_live = tk.BooleanVar(value=False)

        # Generic / UI
        self.logging_level = tk.StringVar(value="INFO")

    def _initialize_variables_from_runtime_config(self):
        """Overlay runtime_config values onto GUI variables using safe accessors."""
        def safe_get(cfg, *keys, default=None):
            cur = cfg
            for k in keys:
                if isinstance(cur, dict) and k in cur:
                    cur = cur[k]
                else:
                    return default
            return cur

        # Example mappings - extend as needed
        try:
            # Logging
            lvl = safe_get(self.runtime_config, "logging", "level", default=None)
            if lvl:
                self.logging_level.set(str(lvl))

            # Backtest data path
            dp = safe_get(self.runtime_config, "backtest", "data_path", default=None)
            if dp:
                self.bt_data_path.set(dp)

            cap = safe_get(self.runtime_config, "backtest", "available_capital", default=None)
            if cap is not None:
                self.bt_available_capital.set(float(cap))

            risk = safe_get(self.runtime_config, "backtest", "risk_percentage", default=None)
            if risk is not None:
                self.bt_risk_percentage.set(float(risk))

            # Indicators
            vwap = safe_get(self.runtime_config, "indicators", "use_vwap", default=None)
            if vwap is not None:
                self.bt_use_vwap.set(bool(vwap))

            ema_on = safe_get(self.runtime_config, "indicators", "use_ema", default=None)
            if ema_on is not None:
                self.bt_use_ema.set(bool(ema_on))

            fast = safe_get(self.runtime_config, "indicators", "ema_fast_period", default=None)
            slow = safe_get(self.runtime_config, "indicators", "ema_slow_period", default=None)
            if fast is not None:
                self.bt_fast_ema_period.set(int(fast))
            if slow is not None:
                self.bt_slow_ema_period.set(int(slow))

            macd_on = safe_get(self.runtime_config, "indicators", "use_macd", default=None)
            if macd_on is not None:
                self.bt_use_macd.set(bool(macd_on))
            mf = safe_get(self.runtime_config, "indicators", "macd_fast", default=None)
            ms = safe_get(self.runtime_config, "indicators", "macd_slow", default=None)
            msig = safe_get(self.runtime_config, "indicators", "macd_signal", default=None)
            if mf is not None:
                self.bt_macd_fast.set(int(mf))
            if ms is not None:
                self.bt_macd_slow.set(int(ms))
            if msig is not None:
                self.bt_macd_signal.set(int(msig))

            # Targets / SL
            tp1 = safe_get(self.runtime_config, "backtest", "tp1_points", default=None)
            if tp1 is not None:
                self.bt_tp1_points.set(float(tp1))
            tp2 = safe_get(self.runtime_config, "backtest", "tp2_points", default=None)
            if tp2 is not None:
                self.bt_tp2_points.set(float(tp2))
            sl = safe_get(self.runtime_config, "backtest", "sl_points", default=None)
            if sl is not None:
                self.bt_sl_points.set(float(sl))

            # Dates
            sd = safe_get(self.runtime_config, "backtest", "start_date", default=None)
            ed = safe_get(self.runtime_config, "backtest", "end_date", default=None)
            if sd:
                self.bt_start_date.set(str(sd))
            if ed:
                self.bt_end_date.set(str(ed))

        except Exception:
            self.logger.exception("Failed to initialize variables from runtime_config")

    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        # Backtest tab
        tb_back = ttk.Frame(nb)
        nb.add(tb_back, text="Backtest")

        row = 0
        ttk.Label(tb_back, text="Data Path:").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(tb_back, textvariable=self.bt_data_path, width=60).grid(row=row, column=1, sticky="w", padx=6)
        ttk.Button(tb_back, text="Browse", command=self._browse_bt_data).grid(row=row, column=2, padx=6)
        row += 1

        ttk.Label(tb_back, text="Available Capital:").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(tb_back, textvariable=self.bt_available_capital).grid(row=row, column=1, sticky="w", padx=6)
        row += 1

        ttk.Label(tb_back, text="Risk %:").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(tb_back, textvariable=self.bt_risk_percentage).grid(row=row, column=1, sticky="w", padx=6)
        row += 1

        # Indicators group
        frm_ind = ttk.LabelFrame(tb_back, text="Indicators")
        frm_ind.grid(row=row, column=0, columnspan=3, sticky="ew", padx=6, pady=6)
        ttk.Checkbutton(frm_ind, text="Use VWAP", variable=self.bt_use_vwap).grid(row=0, column=0, padx=6, pady=2, sticky="w")
        ttk.Checkbutton(frm_ind, text="Use EMA", variable=self.bt_use_ema).grid(row=0, column=1, padx=6, pady=2, sticky="w")
        ttk.Label(frm_ind, text="EMA Fast:").grid(row=1, column=0, sticky="e")
        ttk.Entry(frm_ind, textvariable=self.bt_fast_ema_period, width=6).grid(row=1, column=1, sticky="w")
        ttk.Label(frm_ind, text="EMA Slow:").grid(row=1, column=2, sticky="e")
        ttk.Entry(frm_ind, textvariable=self.bt_slow_ema_period, width=6).grid(row=1, column=3, sticky="w")
        ttk.Checkbutton(frm_ind, text="Use MACD", variable=self.bt_use_macd).grid(row=2, column=0, padx=6, pady=2, sticky="w")

        # Targets / SL
        row += 1
        frm_tgt = ttk.Frame(tb_back)
        frm_tgt.grid(row=row, column=0, columnspan=3, sticky="ew", padx=6, pady=6)
        ttk.Label(frm_tgt, text="TP1 pts:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm_tgt, textvariable=self.bt_tp1_points, width=10).grid(row=0, column=1, sticky="w")
        ttk.Label(frm_tgt, text="TP2 pts:").grid(row=0, column=2, sticky="w")
        ttk.Entry(frm_tgt, textvariable=self.bt_tp2_points, width=10).grid(row=0, column=3, sticky="w")
        ttk.Label(frm_tgt, text="SL pts:").grid(row=0, column=4, sticky="w")
        ttk.Entry(frm_tgt, textvariable=self.bt_sl_points, width=10).grid(row=0, column=5, sticky="w")

        # Dates and Run button
        row += 1
        ttk.Label(tb_back, text="Start Date (YYYY-MM-DD):").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(tb_back, textvariable=self.bt_start_date).grid(row=row, column=1, sticky="w", padx=6)
        row += 1
        ttk.Label(tb_back, text="End Date (YYYY-MM-DD):").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(tb_back, textvariable=self.bt_end_date).grid(row=row, column=1, sticky="w", padx=6)
        row += 1

        ttk.Button(tb_back, text="Run Backtest", command=self.run_backtest).grid(row=row, column=0, padx=6, pady=8)
        ttk.Button(tb_back, text="Build Config (debug)", command=self._print_built_config).grid(row=row, column=1, padx=6, pady=8)

        # Forward / Live tab (minimal)
        tb_live = ttk.Frame(nb)
        nb.add(tb_live, text="Forward / Live")
        ttk.Label(tb_live, text="Account:").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(tb_live, textvariable=self.ft_account).grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(tb_live, text="Trade Size:").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(tb_live, textvariable=self.ft_trade_size).grid(row=1, column=1, sticky="w", padx=6)
        ttk.Checkbutton(tb_live, text="Enable Live", variable=self.ft_enable_live).grid(row=2, column=0, padx=6, pady=6, sticky="w")
        ttk.Button(tb_live, text="Start Live", command=self.run_forward_test).grid(row=3, column=0, padx=6, pady=8)

    def _browse_bt_data(self):
        path = filedialog.askopenfilename(title="Select backtest data file", filetypes=[("CSV files", "*.csv"), ("All", "*.*")])
        if path:
            self.bt_data_path.set(path)

    # ---------- BUILD RUNTIME CONFIG ----------
    def _set_config_value(self, cfg: dict, path: list, value):
        cur = cfg
        for k in path[:-1]:
            cur = cur.setdefault(k, {})
        cur[path[-1]] = value

    def build_runtime_config(self):
        """Assemble runtime config from defaults + current GUI state. No persistence."""
        cfg = copy.deepcopy(self.defaults)

        # explicit mappings (extend as needed)
        try:
            self._set_config_value(cfg, ["backtest", "data_path"], self.bt_data_path.get())
            self._set_config_value(cfg, ["backtest", "available_capital"], float(self.bt_available_capital.get()))
            self._set_config_value(cfg, ["backtest", "risk_percentage"], float(self.bt_risk_percentage.get()))
            self._set_config_value(cfg, ["backtest", "tp1_points"], float(self.bt_tp1_points.get()))
            self._set_config_value(cfg, ["backtest", "tp2_points"], float(self.bt_tp2_points.get()))
            self._set_config_value(cfg, ["backtest", "sl_points"], float(self.bt_sl_points.get()))
            self._set_config_value(cfg, ["backtest", "start_date"], self.bt_start_date.get() or None)
            self._set_config_value(cfg, ["backtest", "end_date"], self.bt_end_date.get() or None)

            # indicators
            self._set_config_value(cfg, ["indicators", "use_vwap"], bool(self.bt_use_vwap.get()))
            self._set_config_value(cfg, ["indicators", "use_ema"], bool(self.bt_use_ema.get()))
            self._set_config_value(cfg, ["indicators", "ema_fast_period"], int(self.bt_fast_ema_period.get()))
            self._set_config_value(cfg, ["indicators", "ema_slow_period"], int(self.bt_slow_ema_period.get()))
            self._set_config_value(cfg, ["indicators", "use_macd"], bool(self.bt_use_macd.get()))
            self._set_config_value(cfg, ["indicators", "macd_fast"], int(self.bt_macd_fast.get()))
            self._set_config_value(cfg, ["indicators", "macd_slow"], int(self.bt_macd_slow.get()))
            self._set_config_value(cfg, ["indicators", "macd_signal"], int(self.bt_macd_signal.get()))

            # forward/live
            self._set_config_value(cfg, ["live", "account"], self.ft_account.get())
            self._set_config_value(cfg, ["live", "trade_size"], float(self.ft_trade_size.get()))
            self._set_config_value(cfg, ["live", "enabled"], bool(self.ft_enable_live.get()))

            # logging level
            self._set_config_value(cfg, ["logging", "level"], self.logging_level.get())

        except Exception:
            self.logger.exception("Failed to build runtime config from GUI")

        return cfg

    # ---------- ACTIONS ----------
    def run_backtest(self):
        cfg = self.build_runtime_config()
        ok, errors = validate_config(cfg)
        if not ok:
            messagebox.showerror("Validation failed", "Configuration validation failed:\n" + "\n".join(errors))
            return
        frozen = freeze_config(cfg)

        try:
            runner = BacktestRunner(frozen)
            runner.run()
            messagebox.showinfo("Backtest", "Backtest finished successfully.")
        except Exception:
            self.logger.exception("Backtest run failed")
            messagebox.showerror("Backtest Error", "Backtest failed. See logs for details.")

    def run_forward_test(self):
        cfg = self.build_runtime_config()
        ok, errors = validate_config(cfg)
        if not ok:
            messagebox.showerror("Validation failed", "Configuration validation failed:\n" + "\n".join(errors))
            return
        frozen = freeze_config(cfg)

        if frozen.get("live", {}).get("enabled"):
            try:
                lt = LiveTrader(frozen)
                lt.start()  # adapt to your LiveTrader API (start/run)
                messagebox.showinfo("Live", "Live trader started.")
            except Exception:
                self.logger.exception("Failed to start LiveTrader")
                messagebox.showerror("Live Error", "Failed to start live trading. See logs.")
        else:
            messagebox.showinfo("Live", "Live trading not enabled. Toggle 'Enable Live' to start.")

    # ---------- Utilities ----------
    def _print_built_config(self):
        cfg = self.build_runtime_config()
        import pprint
        pprint.pprint(cfg)

def main():
    app = UnifiedTradingGUI()
    app.mainloop()


if __name__ == "__main__":
    main()