# scanner_secure_fmp_v4_intraday_news_debug.py

import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# -------------------- CONFIG --------------------
FMP_API_KEY = st.secrets["FMP_API_KEY"]
ALPHA_API_KEY = st.secrets["ALPHA_API_KEY"]
POLYGON_API_KEY = st.secrets["POLYGON_API_KEY"]
DEBUG_MODE = st.secrets.get("ADMIN_DEBUG", False)

# -------------------- FMP v4 Movers --------------------
@st.cache_data(ttl=120)
def fetch_fmp_movers(category="gainers"):
    url = f"https://financialmodelingprep.com/api/v4/stock_market/{category}?apikey={FMP_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if DEBUG_MODE:
            st.write(f"DEBUG FMP {category} Status:", r.status_code)
            st.json(r.json())
        if r.status_code == 200:
            return pd.DataFrame(r.json())
    except Exception as e:
        if DEBUG_MODE:
            st.write(f"DEBUG ERROR FMP {category}:", e)
        st.warning(f"FMP {category} fetch failed.")
    return pd.DataFrame()

# -------------------- Alpha Vantage Intraday --------------------
@st.cache_data(ttl=300)
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
        st.warning(f"Alpha Vantage intraday fetch failed for {symbol}.")
    return pd.DataFrame()

# -------------------- Polygon News --------------------
@st.cache_data(ttl=900)
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
        st.warning("Polygon news fetch failed.")
    return []

# -------------------- STREAMLIT UI --------------------
def main():
    st.set_page_config(page_title="Tadi's Market Scanner (FMP v4)", layout="wide")
    st_autorefresh(interval=60000, limit=100, key="refresh")

    st.title("📈 Tadi's Market Scanner")
    st.caption("Powered by FMP v4 movers, Alpha Vantage intraday, and Polygon news")

    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(f"**Last Updated:** {last_updated}")

    tab_movers, tab_charts, tab_news = st.tabs(["📊 Market Movers", "📈 Charts", "📰 News"])

    # Fetch data
    gainers = fetch_fmp_movers("gainers")
    losers = fetch_fmp_movers("losers")
    actives = fetch_fmp_movers("actives")

    # Market Movers Tab
    with tab_movers:
        st.header("Top Market Movers")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🚀 Gainers")
            if not gainers.empty:
                st.dataframe(gainers, use_container_width=True)
                if "changesPercentage" in gainers.columns:
                    st.bar_chart(gainers.set_index("symbol")["changesPercentage"].head(10))
            else:
                st.info("No gainers data available right now.")

        with col2:
            st.subheader("📉 Losers")
            if not losers.empty:
                st.dataframe(losers, use_container_width=True)
                if "changesPercentage" in losers.columns:
                    st.bar_chart(losers.set_index("symbol")["changesPercentage"].head(10))
            else:
                st.info("No losers data available right now.")

        st.subheader("🔥 Most Active")
        if not actives.empty:
            st.dataframe(actives, use_container_width=True)
        else:
            st.info("No active stocks data available right now.")

    # Charts Tab
    with tab_charts:
        st.header("Intraday Chart for Top Gainer")
        if not gainers.empty:
            top_symbol = gainers.iloc[0]["symbol"]
            st.subheader(f"📈 Intraday (5min) Chart for {top_symbol}")
            ohlc = fetch_alpha_intraday(top_symbol)
            if not ohlc.empty:
                st.line_chart(ohlc["4. close"])
            else:
                st.info(f"No intraday data available for {top_symbol}.")
        else:
            st.info("No chart data available right now.")

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













