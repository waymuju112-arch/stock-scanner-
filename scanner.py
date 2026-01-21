# hybrid_scanner_polygon_alpha.py

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# -------------------- CONFIG --------------------
POLYGON_API_KEY = st.secrets["POLYGON_API_KEY"]
ALPHA_API_KEY = st.secrets["ALPHA_API_KEY"]
DEBUG_MODE = st.secrets.get("ADMIN_DEBUG", False)

# -------------------- Polygon Movers --------------------
@st.cache_data(ttl=900)  # cache for 15 minutes
def fetch_polygon_movers(direction="gainers"):
    url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/{direction}?apiKey={POLYGON_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if DEBUG_MODE:
            st.write(f"DEBUG Polygon {direction}:", r.status_code)
            st.json(r.json())
        if r.status_code == 200:
            return pd.DataFrame(r.json().get("tickers", []))
        elif r.status_code == 429:  # quota exceeded
            st.warning("Polygon quota exceeded. Switching to fallback watchlist.")
            return None
    except Exception as e:
        if DEBUG_MODE:
            st.write(f"DEBUG ERROR Polygon {direction}:", e)
    return None

# -------------------- Alpha Vantage Intraday --------------------
@st.cache_data(ttl=120)  # cache for 2 minutes
def fetch_alpha_intraday(symbol):
    url = (
        f"https://www.alphavantage.co/query?"
        f"function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&apikey={ALPHA_API_KEY}&outputsize=compact"
    )
    try:
        r = requests.get(url, timeout=10)
        if DEBUG_MODE:
            st.write("DEBUG Alpha Intraday:", r.status_code)
            st.json(r.json())
        if r.status_code == 200:
            data = r.json().get("Time Series (5min)", {})
            if data:
                df = pd.DataFrame.from_dict(data, orient="index").astype(float)
                df.index = pd.to_datetime(df.index)
                return df.sort_index()
    except Exception as e:
        if DEBUG_MODE:
            st.write("DEBUG ERROR Alpha Intraday:", e)
    return pd.DataFrame()

# -------------------- Fallback Watchlist Movers --------------------
def compute_watchlist_movers(watchlist):
    movers = []
    for symbol in watchlist:
        df = fetch_alpha_intraday(symbol)
        if not df.empty:
            latest = df.iloc[-1]["4. close"]
            prev = df.iloc[0]["4. close"]
            change_pct = ((latest - prev) / prev) * 100
            movers.append({"symbol": symbol, "latest": latest, "change_pct": change_pct})
    return pd.DataFrame(movers)

# -------------------- STREAMLIT UI --------------------
def main():
    st.set_page_config(page_title="Hybrid Market Scanner", layout="wide")

    st.title("📈 Hybrid Market Scanner")
    st.caption("Polygon movers + Alpha Vantage intraday, with fallback watchlist")

    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(f"**Last Updated:** {last_updated}")

    # Manual refresh button
    if st.button("🔄 Refresh Movers"):
        st.cache_data.clear()  # clear cache to force fresh fetch

    tab_movers, tab_charts = st.tabs(["📊 Market Movers", "📈 Charts"])

    # Fetch movers
    gainers = fetch_polygon_movers("gainers")
    losers = fetch_polygon_movers("losers")

    # Fallback if quota exceeded
    if gainers is None or losers is None:
        watchlist = ["AAPL", "MSFT", "TSLA", "AMZN", "NVDA"]  # customizable
        st.info("Using fallback watchlist movers")
        gainers = compute_watchlist_movers(watchlist)
        losers = pd.DataFrame()  # optional

    # Movers Tab
    with tab_movers:
        st.header("Top Market Movers")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🚀 Gainers")
            if gainers is not None and not gainers.empty:
                st.dataframe(gainers, use_container_width=True)
                if "change_pct" in gainers.columns:
                    st.bar_chart(gainers.set_index("symbol")["change_pct"].head(10))
            else:
                st.info("No gainers data available.")

        with col2:
            st.subheader("📉 Losers")
            if losers is not None and not losers.empty:
                st.dataframe(losers, use_container_width=True)
                if "change_pct" in losers.columns:
                    st.bar_chart(losers.set_index("symbol")["change_pct"].head(10))
            else:
                st.info("No losers data available.")

    # Charts Tab
    with tab_charts:
        st.header("Intraday Chart for Selected Symbol")
        symbol = st.text_input("Enter a ticker (e.g., AAPL, TSLA):", "AAPL")
        ohlc = fetch_alpha_intraday(symbol)
        if not ohlc.empty:
            st.line_chart(ohlc["4. close"])
        else:
            st.info(f"No intraday data available for {symbol}.")

if __name__ == "__main__":
    main()











