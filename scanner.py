# scanner_watchlist_alpha_news.py

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# -------------------- CONFIG --------------------
ALPHA_API_KEY = st.secrets["ALPHA_API_KEY"]
POLYGON_API_KEY = st.secrets["POLYGON_API_KEY"]
DEBUG_MODE = st.secrets.get("ADMIN_DEBUG", False)

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

# -------------------- Compute Movers from Watchlist --------------------
def compute_watchlist_movers(watchlist):
    movers = []
    for symbol in watchlist:
        df = fetch_alpha_intraday(symbol)
        if not df.empty:
            latest = df.iloc[-1]["4. close"]
            prev = df.iloc[0]["4. close"]
            change_pct = ((latest - prev) / prev) * 100
            movers.append({"symbol": symbol, "latest": latest, "change_pct": change_pct})
    movers_df = pd.DataFrame(movers)
    if not movers_df.empty:
        gainers = movers_df.sort_values("change_pct", ascending=False).head(5)
        losers = movers_df.sort_values("change_pct", ascending=True).head(5)
        return gainers, losers
    return pd.DataFrame(), pd.DataFrame()

# -------------------- Polygon News --------------------
@st.cache_data(ttl=900)  # cache for 15 minutes
def fetch_polygon_news():
    url = f"https://api.polygon.io/v2/reference/news?apiKey={POLYGON_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if DEBUG_MODE:
            st.write("DEBUG Polygon News:", r.status_code)
            st.json(r.json())
        if r.status_code == 200 and "application/json" in r.headers.get("Content-Type", ""):
            return r.json().get("results", [])
    except Exception as e:
        if DEBUG_MODE:
            st.write("DEBUG ERROR Polygon News:", e)
    return []

# -------------------- STREAMLIT UI --------------------
def main():
    st.set_page_config(page_title="Watchlist Market Scanner", layout="wide")

    st.title("📈 Watchlist Market Scanner")
    st.caption("Alpha Vantage intraday movers + Polygon news")

    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(f"**Last Updated:** {last_updated}")

    tab_movers, tab_charts, tab_news = st.tabs(["📊 Watchlist Movers", "📈 Charts", "📰 News"])

    # Curated watchlist (customize here)
    watchlist = ["AAPL", "MSFT", "TSLA", "AMZN", "NVDA"]

    # Movers Tab
    with tab_movers:
        st.header("Watchlist Movers")
        gainers, losers = compute_watchlist_movers(watchlist)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🚀 Gainers")
            if not gainers.empty:
                st.dataframe(gainers, use_container_width=True)
                st.bar_chart(gainers.set_index("symbol")["change_pct"])
            else:
                st.info("No gainers data available.")

        with col2:
            st.subheader("📉 Losers")
            if not losers.empty:
                st.dataframe(losers, use_container_width=True)
                st.bar_chart(losers.set_index("symbol")["change_pct"])
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

    # News Tab
    with tab_news:
        st.header("Latest Market News")
        news = fetch_polygon_news()
        if news:
            for article in news[:10]:
                with st.expander(article.get("title", "News Item")):
                    image_url = article.get("image_url")
                    if image_url:
                        st.image(image_url, width=200)
                    st.write(article.get("description", ""))
                    url = article.get("article_url")
                    if url:
                        st.markdown(f"[Read more]({url})")
        else:
            st.info("No news available right now.")

if __name__ == "__main__":
    main()









