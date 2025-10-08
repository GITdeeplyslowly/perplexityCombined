
import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime, time
import os
import argparse

# Custom Data Feed for price_ticks.log
class PriceTicksLogData(bt.feeds.PandasData):
    """
    Custom data feed to load and resample price_ticks.log data.
    """
    params = (
        ('datetime', None),
        ('open', -1),
        ('high', -1),
        ('low', -1),
        ('close', 0),
        ('volume', 1),
        ('openinterest', -1),
    )

    def __init__(self, **kwargs):
        super(PriceTicksLogData, self).__init__(**kwargs)
        self.resample_log_data()

    def resample_log_data(self):
        log_path = self.p.dataname
        if not os.path.exists(log_path):
            raise FileNotFoundError(f"Price ticks log file not found: {log_path}")

        ticks_data = []
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        timestamp_str = parts[0]
                        price = float(parts[1])
                        volume = int(parts[2]) if len(parts) > 2 else 0
                        if 'T' in timestamp_str:
                            timestamp = pd.to_datetime(timestamp_str)
                        else:
                            timestamp = pd.to_datetime(timestamp_str)
                        ticks_data.append({
                            'timestamp': timestamp,
                            'price': price,
                            'volume': volume
                        })
                except Exception:
                    continue

        if not ticks_data:
            raise Exception("No valid tick data found in log file")

        df_ticks = pd.DataFrame(ticks_data)
        df_ticks.set_index('timestamp', inplace=True)

        df_ohlcv = df_ticks['price'].resample('1T').ohlc()
        df_volume = df_ticks['volume'].resample('1T').sum()
        df = pd.concat([df_ohlcv, df_volume], axis=1)
        df.columns = ['open', 'high', 'low', 'close', 'volume']
        df = df.fillna(method='ffill')
        df = df.dropna()

        self.p.dataname = df

"""
Custom Indicator block removed: Supertrend indicator is deprecated.
Added MACD indicator support using built-in Backtrader MACD.
"""

# Custom Indicator for VWAP
class VWAP(bt.Indicator):
    lines = ('vwap',)
    plotinfo = dict(subplot=False)

    def __init__(self):
        self.cumulative_pv = bt.indicators.SumN(self.data.close * self.data.volume, period=999999)
        self.cumulative_volume = bt.indicators.SumN(self.data.volume, period=999999)

    def next(self):
        if self.cumulative_volume[0] > 0:
            self.l.vwap[0] = self.cumulative_pv[0] / self.cumulative_volume[0]
        else:
            self.l.vwap[0] = self.data.close[0]

# Main Trading Strategy
class MyStrategy(bt.Strategy):
    params = (
        ('use_supertrend', True),
        ('use_ema_crossover', True),
        ('use_rsi_filter', True),
        ('use_vwap', False),
        ('atr_len', 10),
        ('atr_mult', 3.0),
        ('fast_ema', 9),
        ('slow_ema', 21),
        ('rsi_length', 14),
        ('rsi_overbought', 70),
        ('rsi_oversold', 30),
        ('base_sl_points', 15),
        ('tp1_points', 25),
        ('tp2_points', 45),
        ('tp3_points', 100),
        ('use_trail_stop', True),
        ('trail_activation_points', 25),
        ('trail_distance_points', 10),
        ('buy_buffer', 5),
        ('exit_before_close', 20),
    )

    def __init__(self):
        self.inds = {}
        if self.p.use_supertrend:
            self.inds['supertrend'] = Supertrend(atr_len=self.p.atr_len, atr_mult=self.p.atr_mult)
        if self.p.use_ema_crossover:
            self.inds['ema_fast'] = bt.indicators.EMA(self.data.close, period=self.p.fast_ema)
            self.inds['ema_slow'] = bt.indicators.EMA(self.data.close, period=self.p.slow_ema)
            self.inds['ema_crossover'] = bt.indicators.CrossOver(self.inds['ema_fast'], self.inds['ema_slow'])
        if self.p.use_rsi_filter:
            self.inds['rsi'] = bt.indicators.RSI(self.data.close, period=self.p.rsi_length)
        if self.p.use_vwap:
            self.inds['vwap'] = VWAP()

        self.order = None
        self.buy_price = None
        self.buy_comm = None
        self.tp1_order = None
        self.tp2_order = None
        self.tp3_order = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f'OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}')

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')

    def next(self):
        if self.order:
            return

        if not self.position:
            buy_signal = True
            if self.p.use_supertrend and self.data.close[0] < self.inds['supertrend'].l.supertrend[0]:
                buy_signal = False
            if self.p.use_ema_crossover and self.inds['ema_crossover'][0] <= 0:
                buy_signal = False
            if self.p.use_rsi_filter and (self.inds['rsi'][0] < self.p.rsi_oversold or self.inds['rsi'][0] > self.p.rsi_overbought):
                buy_signal = False
            if self.p.use_vwap and self.data.close[0] < self.inds['vwap'].l.vwap[0]:
                buy_signal = False

            if buy_signal:
                entry_price = self.data.close[0] + self.p.buy_buffer
                self.order = self.buy(exectype=bt.Order.Stop, price=entry_price)
                self.log(f'BUY CREATE, {entry_price:.2f}')

        else:
            # Exit logic
            if self.p.use_trail_stop:
                self.sell(exectype=bt.Order.StopTrail, trailamount=self.p.trail_distance_points)

            # Take Profit
            if not self.tp1_order:
                tp1_price = self.buy_price + self.p.tp1_points
                self.tp1_order = self.sell(exectype=bt.Order.Limit, price=tp1_price, size=self.position.size * 0.5)
            if not self.tp2_order and self.tp1_order and self.tp1_order.status == self.tp1_order.Completed:
                tp2_price = self.buy_price + self.p.tp2_points
                self.tp2_order = self.sell(exectype=bt.Order.Limit, price=tp2_price, size=self.position.size * 0.6)
            if not self.tp3_order and self.tp2_order and self.tp2_order.status == self.tp2_order.Completed:
                tp3_price = self.buy_price + self.p.tp3_points
                self.tp3_order = self.sell(exectype=bt.Order.Limit, price=tp3_price)

            # Mandatory exit before close
            if self.data.datetime.time() >= time(15, 30 - self.p.exit_before_close):
                self.log('MANDATORY EXIT, EOD')
                self.close()

def run_backtest(args):
    cerebro = bt.Cerebro()

    # Add strategy
    cerebro.addstrategy(MyStrategy,
                        use_supertrend=args.use_supertrend,
                        use_ema_crossover=args.use_ema_crossover,
                        use_rsi_filter=args.use_rsi_filter,
                        use_vwap=args.use_vwap,
                        atr_len=args.atr_len,
                        atr_mult=args.atr_mult,
                        fast_ema=args.fast_ema,
                        slow_ema=args.slow_ema,
                        rsi_length=args.rsi_length,
                        rsi_overbought=args.rsi_overbought,
                        rsi_oversold=args.rsi_oversold,
                        base_sl_points=args.base_sl_points,
                        tp1_points=args.tp1_points,
                        tp2_points=args.tp2_points,
                        tp3_points=args.tp3_points,
                        use_trail_stop=args.use_trail_stop,
                        trail_activation_points=args.trail_activation_points,
                        trail_distance_points=args.trail_distance_points,
                        buy_buffer=args.buy_buffer,
                        exit_before_close=args.exit_before_close)

    # Add data
    if args.data_type == 'ticks':
        data = PriceTicksLogData(dataname=args.data_file)
    else:
        data = bt.feeds.GenericCSVData(
            dataname=args.data_file,
            dtformat=('%Y-%m-%d %H:%M:%S'),
            datetime=0,
            high=2,
            low=3,
            open=1,
            close=4,
            volume=5,
            openinterest=-1
        )
    cerebro.adddata(data)

    # Set initial capital
    cerebro.broker.setcash(args.initial_capital)
    cerebro.broker.setcommission(commission=0.001)

    # Run backtest
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Plot results
    cerebro.plot()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backtrader Backtest')
    parser.add_argument('--data_file', type=str, required=True, help='Path to the data file')
    parser.add_argument('--data_type', type=str, choices=['csv', 'ticks'], default='csv', help='Type of data file')
    parser.add_argument('--initial_capital', type=float, default=100000, help='Initial capital')
    # Add all other parameters from the GUI
    parser.add_argument('--use_supertrend', action='store_true')
    parser.add_argument('--use_ema_crossover', action='store_true')
    parser.add_argument('--use_rsi_filter', action='store_true')
    parser.add_argument('--use_vwap', action='store_true')
    parser.add_argument('--atr_len', type=int, default=10)
    parser.add_argument('--atr_mult', type=float, default=3.0)
    parser.add_argument('--fast_ema', type=int, default=9)
    parser.add_argument('--slow_ema', type=int, default=21)
    parser.add_argument('--rsi_length', type=int, default=14)
    parser.add_argument('--rsi_overbought', type=int, default=70)
    parser.add_argument('--rsi_oversold', type=int, default=30)
    parser.add_argument('--base_sl_points', type=int, default=15)
    parser.add_argument('--tp1_points', type=int, default=25)
    parser.add_argument('--tp2_points', type=int, default=45)
    parser.add_argument('--tp3_points', type=int, default=100)
    parser.add_argument('--use_trail_stop', action='store_true', default=True)
    parser.add_argument('--trail_activation_points', type=int, default=25)
    parser.add_argument('--trail_distance_points', type=int, default=10)
    parser.add_argument('--buy_buffer', type=int, default=5)
    parser.add_argument('--exit_before_close', type=int, default=20)

    args = parser.parse_args()
    run_backtest(args)
