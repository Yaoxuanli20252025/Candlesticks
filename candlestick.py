"""
Candlestick chart visualizer.

Usage:
  python3 candlestick.py --source file              # read from data.csv
  python3 candlestick.py --source api --ticker AAPL # fetch from Yahoo Finance
  python3 candlestick.py --source api --ticker AAPL --period 1mo --interval 1d
"""

import argparse
import sys
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── CLI args ──────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Candlestick chart")
parser.add_argument("--source", choices=["file", "api"], default="file",
                    help="Data source: 'file' (data.csv) or 'api' (Yahoo Finance)")
parser.add_argument("--file", default="data.csv", help="CSV file path (file mode)")
parser.add_argument("--ticker", default="AAPL", help="Ticker symbol (api mode)")
parser.add_argument("--period", default="5d",
                    help="yfinance period: 1d 5d 1mo 3mo 6mo 1y 2y 5y 10y ytd max")
parser.add_argument("--interval", default="1h",
                    help="yfinance interval: 1m 2m 5m 15m 30m 60m 90m 1h 1d 5d 1wk 1mo")
args = parser.parse_args()


# ── Load data ─────────────────────────────────────────────────────────────────
def load_file(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["timestamp"], dayfirst=True)
    df = df.rename(columns={"timestamp": "Date", "open": "Open", "high": "High",
                             "low": "Low", "close": "Close"})
    df = df.sort_values("Date").reset_index(drop=True)
    return df


def load_api(ticker: str, period: str, interval: str) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError:
        sys.exit("yfinance not installed. Run: pip3 install yfinance")
    print(f"Fetching {ticker} ({period}, {interval}) from Yahoo Finance…")
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
    if df.empty:
        sys.exit(f"No data returned for ticker '{ticker}'. Check the symbol or period.")
    df = df.reset_index().rename(columns={"index": "Date", "Datetime": "Date"})
    # Flatten MultiIndex columns if present (yfinance ≥0.2)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    return df[["Date", "Open", "High", "Low", "Close"]]


if args.source == "file":
    df = load_file(args.file)
    title = f"Candlestick — {args.file}"
else:
    df = load_api(args.ticker, args.period, args.interval)
    title = f"Candlestick — {args.ticker.upper()}  ({args.period}, {args.interval})"

print(f"Loaded {len(df)} rows  |  {df['Date'].iloc[0]} → {df['Date'].iloc[-1]}")


# ── Compute indicators ────────────────────────────────────────────────────────
df["MA20"] = df["Close"].rolling(20).mean()
df["MA50"] = df["Close"].rolling(50).mean()
df["change"] = df["Close"].diff()
bar_colors = ["#26a69a" if c >= 0 else "#ef5350" for c in df["change"]]


# ── Build figure ──────────────────────────────────────────────────────────────
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    row_heights=[0.75, 0.25],
    vertical_spacing=0.03,
    subplot_titles=(title, "Price Change"),
)

# Candlestick
fig.add_trace(
    go.Candlestick(
        x=df["Date"],
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="OHLC",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
    ),
    row=1, col=1,
)

# Moving averages
if df["MA20"].notna().any():
    fig.add_trace(
        go.Scatter(x=df["Date"], y=df["MA20"], name="MA20",
                   line=dict(color="orange", width=1.2)),
        row=1, col=1,
    )
if df["MA50"].notna().any():
    fig.add_trace(
        go.Scatter(x=df["Date"], y=df["MA50"], name="MA50",
                   line=dict(color="royalblue", width=1.2)),
        row=1, col=1,
    )

# Price-change bars
fig.add_trace(
    go.Bar(
        x=df["Date"],
        y=df["change"].abs(),
        name="Price Change",
        marker_color=bar_colors,
        showlegend=False,
    ),
    row=2, col=1,
)

# ── Layout ────────────────────────────────────────────────────────────────────
fig.update_layout(
    height=700,
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=60, r=30, t=60, b=40),
)
fig.update_yaxes(title_text="Price", row=1, col=1)
fig.update_yaxes(title_text="|Change|", row=2, col=1)

output_file = "candlestick.html"
fig.write_html(output_file)
print(f"Chart saved → {output_file}")
fig.show()
