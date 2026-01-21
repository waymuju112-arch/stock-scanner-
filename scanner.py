# scanner_sp500_safe.py

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# -------------------- CONFIG --------------------
ALPHA_API_KEY = st.secrets["ALPHA_API_KEY"]
POLYGON_API_KEY = st.secrets["POLYGON_API_KEY"]
DEBUG_MODE = st.secrets.get("ADMIN_DEBUG", False)

# -------------------- Load Universe from CSV --------------------
@st.cache_data(ttl=86400)
def load_sp500_universe():
    try:
        df = pd.read_csv("sp500.csv")
        return df["Symbol"].dropna().unique().tolist()
    except Exception as e:
        st.warning("Failed to load sp500.csv, falling back to default list.")
        if DEBUG_MODE:
            st.write("DEBUG CSV ERROR:", e)
        return ["AAPL","MSFT","TSLA","AMZN","NVDA"]

# -------------------- Alpha Vantage Daily OHLC --------------------
@st.cache_data(ttl=1800)
def fetch_alpha_daily(symbol):
    url = (
        f"https://www.alphavantage.co/query?"
        f"function=TIME_SERIES_DAILY&symbol={symbol}&apikey={ALPHA_API_KEY}&outputsize=compact"
    )
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json().get("Time Series (Daily)", {})
            if data:
                df = pd.DataFrame.from_dict(data, orient="index").astype(float)
                df.index = pd.to_datetime(df.index)
                return df.sort_index()
    except Exception as e:
        if DEBUG_MODE:
            st.write(f"DEBUG ERROR Alpha Daily {symbol}:", e)
    return pd.DataFrame()

# -------------------- Alpha Vantage Intraday (Hourly) --------------------
@st.cache_data(ttl=600)
def fetch_alpha_intraday(symbol):
    url = (
        f"https://www.alphavantage.co/query?"
        f"function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=60min&apikey={ALPHA_API_KEY}&outputsize=full"
    )
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json().get("Time Series (60min)", {})
            if data:
                df = pd.DataFrame.from_dict(data, orient="index").astype(float)
                df.index = pd.to_datetime(df.index)
                return df.sort_index()
    except Exception as e:
        if DEBUG_MODE:
            st.write(f"DEBUG ERROR Alpha Intraday {symbol}:", e)
    return pd.DataFrame()

# -------------------- Compute Movers --------------------
def compute_daily_movers(universe):
    movers = []
    progress = st.progress(0)
    for i, symbol in enumerate(universe):
        df = fetch_alpha_daily(symbol)
        if df.empty or len(df) < 20:
            continue
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        avg_vol = df["5. volume"].tail(20).mean()
        rel_vol = latest["5. volume"] / avg_vol if avg_vol > 0 else 0
        change_pct = ((latest["4. close"] - prev["4. close"]) / prev["4. close"]) * 100
        movers.append({
            "ticker": symbol,
            "price": round(latest["4. close"], 2),
            "change_percent": round(change_pct, 2),
            "volume": int(latest["5. volume"]),
            "relative_volume": round(rel_vol, 2)
        })
        progress.progress((i+1)/len(universe))
    movers_df = pd.DataFrame(movers)
    if not movers_df.empty:
        gainers = movers_df.sort_values("change_percent", ascending=False).head(10)
        losers = movers_df.sort_values("change_percent", ascending=True).head(10)
        actives = movers_df.sort_values("volume", ascending=False).head(10)
        return gainers, losers, actives, movers_df
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# -------------------- Polygon News --------------------
@st.cache_data(ttl=900)
def fetch_polygon_news():
    url = f"https://api.polygon.io/v2/reference/news?apiKey={POLYGON_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json().get("results", [])
    except Exception as e:
        if DEBUG_MODE:
            st.write("DEBUG ERROR Polygon News:", e)
    return []

# -------------------- STREAMLIT UI --------------------
def main():
    st.set_page_config(page_title="S&P 500 Dashboard", layout="wide")
    st.title("📊 S&P 500 Demand/Supply Dashboard")

    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Last Updated: {last_updated}")

    # Universe
    universe = load_sp500_universe()
    gainers, losers, actives, movers_df = compute_daily_movers(universe)

    # Quick Metrics
    if not movers_df.empty:
        col1, col2, col3 = st.columns(3)
        if not gainers.empty and "change_percent" in gainers.columns:
            col1.metric("Top Gainer", gainers.iloc[0]["ticker"], f"{gainers.iloc[0]['change_percent']}%")
        if not losers.empty and "change_percent" in losers.columns:
            col2.metric("Top Loser", losers.iloc[0]["ticker"], f"{losers.iloc[0]['change_percent']}%")
        if not actives.empty and "volume" in actives.columns:
            col3.metric("Most Active", actives.iloc[0]["ticker"], f"{actives.iloc[0]['volume']:,}")

    # Tabs
    tab_movers, tab_charts, tab_news = st.tabs(["📈 Movers", "📉 Charts", "📰 News"])

    # Movers Tab
    with tab_movers:
        st.subheader("🚀 Gainers")
        if not gainers.empty and "change_percent" in gainers.columns:
            st.dataframe(gainers.style.background_gradient(subset=["change_percent"], cmap="Greens"))
        elif not gainers.empty:
            st.dataframe(gainers)
        else:
            st.info("No gainers available.")

        st.subheader("📉 Losers")
        if not losers.empty and "change_percent" in losers.columns:
            st.dataframe(losers.style.background_gradient(subset=["change_percent"], cmap="Reds"))
        elif not losers.empty:
            st.dataframe(losers)
        else:
            st.info("No losers available.")

        st.subheader("🔥 Most Active")
        if not actives.empty and "volume" in actives.columns:
            st.dataframe(actives.style.background_gradient(subset=["volume"], cmap="Blues"))
        elif not actives.empty:
            st.dataframe(actives)
        else:
            st.info("No active stocks available.")

    # Charts Tab
    with tab_charts:
        st.subheader("Hourly Bar Chart")
        symbol = st.text_input("Enter a ticker:", "AAPL")
        df = fetch_alpha_intraday(symbol)
        if not df.empty:
            yesterday = df.index[-1].date()
            df_yday = df[df.index.date == yesterday]
            st.bar_chart(df_yday["4. close"])
        else:
            st.info(f"No intraday data for {symbol}.")

    # News Tab
    with tab_news:
        st.subheader("Latest Market News")
        news = fetch_polygon_news()
        if news:
            for article in news[:8]:
                st.markdown("---")
                col1, col2 = st.columns([1,3])
                with col1:
                    image_url = article.get("image_url")
                    if image_url:
                        st.image(image_url, use_container_width=True)
                with col2:
                    st.markdown(f"### {article.get('title','News Item')}")
                    st.write(article.get("description",""))
                    url = article.get("article_url")
                    if url:
                        st.markdown(f"[🔗 Read more]({url})")
        else:
            st.info("No news available.")

if __name__ == "__main__":
    main()











