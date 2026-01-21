# scanner_forex.py

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# -------------------- CONFIG --------------------
ALPHA_API_KEY = st.secrets["ALPHA_API_KEY"]
POLYGON_API_KEY = st.secrets["POLYGON_API_KEY"]
DEBUG_MODE = st.secrets.get("ADMIN_DEBUG", False)

# -------------------- Load Forex Universe --------------------
@st.cache_data(ttl=86400)
def load_forex_universe():
    # Example CSV: forex_pairs.csv with column "Pair" like EURUSD, GBPUSD, USDJPY
    df = pd.read_csv("forex_pairs.csv")
    return df["Pair"].dropna().unique().tolist()

# -------------------- Alpha Vantage FX Daily --------------------
@st.cache_data(ttl=1800)
def fetch_fx_daily(pair):
    from_symbol = pair[:3]
    to_symbol = pair[3:]
    url = (
        f"https://www.alphavantage.co/query?"
        f"function=FX_DAILY&from_symbol={from_symbol}&to_symbol={to_symbol}&apikey={ALPHA_API_KEY}&outputsize=compact"
    )
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json().get("Time Series FX (Daily)", {})
            if data:
                df = pd.DataFrame.from_dict(data, orient="index").astype(float)
                df.index = pd.to_datetime(df.index)
                return df.sort_index()
    except Exception as e:
        if DEBUG_MODE:
            st.write(f"DEBUG ERROR FX Daily {pair}:", e)
    return pd.DataFrame()

# -------------------- Alpha Vantage FX Intraday --------------------
@st.cache_data(ttl=600)
def fetch_fx_intraday(pair):
    from_symbol = pair[:3]
    to_symbol = pair[3:]
    url = (
        f"https://www.alphavantage.co/query?"
        f"function=FX_INTRADAY&from_symbol={from_symbol}&to_symbol={to_symbol}&interval=60min&apikey={ALPHA_API_KEY}&outputsize=full"
    )
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json().get("Time Series FX (60min)", {})
            if data:
                df = pd.DataFrame.from_dict(data, orient="index").astype(float)
                df.index = pd.to_datetime(df.index)
                return df.sort_index()
    except Exception as e:
        if DEBUG_MODE:
            st.write(f"DEBUG ERROR FX Intraday {pair}:", e)
    return pd.DataFrame()

# -------------------- Compute Movers --------------------
def compute_fx_movers(universe):
    movers = []
    progress = st.progress(0)
    for i, pair in enumerate(universe):
        df = fetch_fx_daily(pair)
        if df.empty or len(df) < 2:
            continue
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        change_pct = ((latest["4. close"] - prev["4. close"]) / prev["4. close"]) * 100
        movers.append({
            "pair": pair,
            "price": round(latest["4. close"], 5),
            "change_percent": round(change_pct, 3)
        })
        progress.progress((i+1)/len(universe))
    movers_df = pd.DataFrame(movers)
    if not movers_df.empty:
        gainers = movers_df.sort_values("change_percent", ascending=False).head(5)
        losers = movers_df.sort_values("change_percent", ascending=True).head(5)
        actives = movers_df.sort_values("price", ascending=False).head(5)  # proxy: highest price pairs
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
    st.set_page_config(page_title="Forex Dashboard", layout="wide")
    st.title("💱 Forex Demand/Supply Dashboard")

    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Last Updated: {last_updated}")

    # Universe
    universe = load_forex_universe()
    gainers, losers, actives, movers_df = compute_fx_movers(universe)

    # Quick Metrics (blips at the top)
    if not movers_df.empty:
        col1, col2, col3 = st.columns(3)
        if not gainers.empty:
            col1.metric("Top Gainer", gainers.iloc[0]["pair"], f"{gainers.iloc[0]['change_percent']}%")
        if not losers.empty:
            col2.metric("Top Loser", losers.iloc[0]["pair"], f"{losers.iloc[0]['change_percent']}%")
        if not actives.empty:
            col3.metric("Highest Price", actives.iloc[0]["pair"], f"{actives.iloc[0]['price']}")

    # Tabs
    tab_movers, tab_charts, tab_news = st.tabs(["📈 Movers", "📉 Charts", "📰 News"])

    # Movers Tab
    with tab_movers:
        st.subheader("🚀 Gainers")
        if not gainers.empty and "change_percent" in gainers.columns:
            st.dataframe(gainers.style.background_gradient(subset=["change_percent"], cmap="Greens"))
        else:
            st.info("No gainers available.")
        st.subheader("📉 Losers")
        if not losers.empty and "change_percent" in losers.columns:
            st.dataframe(losers.style.background_gradient(subset=["change_percent"], cmap="Reds"))
        else:
            st.info("No losers available.")
        st.subheader("💲 Highest Price Pairs")
        if not actives.empty and "price" in actives.columns:
            st.dataframe(actives.style.background_gradient(subset=["price"], cmap="Blues"))
        else:
            st.info("No active pairs available.")

    # Charts Tab
    with tab_charts:
        st.subheader("Hourly Bar Chart")
        pair = st.text_input("Enter a forex pair (e.g., EURUSD):", "EURUSD")
        df = fetch_fx_intraday(pair)
        if not df.empty:
            yesterday = df.index[-1].date()
            df_yday = df[df.index.date == yesterday]
            st.bar_chart(df_yday["4. close"])
        else:
            st.info(f"No intraday data for {pair}.")

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












