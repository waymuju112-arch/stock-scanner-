# scanner_forex_snapshot.py

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import feedparser   # for forex RSS feeds

# -------------------- CONFIG --------------------
ALPHA_API_KEY = st.secrets["ALPHA_API_KEY"]
DEBUG_MODE = st.secrets.get("ADMIN_DEBUG", False)

# -------------------- Load Forex Universe --------------------
@st.cache_data(ttl=86400)
def load_forex_universe():
    try:
        df = pd.read_csv("forex_pairs.csv")
        return df["Pair"].dropna().unique().tolist()
    except FileNotFoundError:
        # fallback list
        return ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD","USDCHF","NZDUSD","USDZAR",
                "EURJPY","EURGBP","EURAUD","AUDJPY","GBPJPY","CHFJPY","EURCAD","GBPCAD",
                "AUDNZD","USDTRY","USDMXN"]

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

# -------------------- Compute Movers Snapshot --------------------
def compute_fx_movers(universe):
    movers = []
    for pair in universe:
        df = fetch_fx_daily(pair)
        if df.empty or len(df) < 2:
            continue
        latest = df.iloc[-1]   # yesterday
        prev = df.iloc[-2]     # day before yesterday
        change_pct = ((latest["4. close"] - prev["4. close"]) / prev["4. close"]) * 100
        movers.append({
            "pair": pair,
            "price": round(latest["4. close"], 5),
            "change_percent": round(change_pct, 3)
        })
    movers_df = pd.DataFrame(movers)
    if not movers_df.empty:
        movers_df["abs_change"] = movers_df["change_percent"].abs()
        gainers = movers_df.sort_values("change_percent", ascending=False).head(5)
        losers = movers_df.sort_values("change_percent", ascending=True).head(5)
        actives = movers_df.sort_values("abs_change", ascending=False).head(5)
        return gainers, losers, actives, movers_df
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# -------------------- Forex News via FXStreet RSS --------------------
@st.cache_data(ttl=900)
def fetch_forex_news():
    feed_url = "https://www.fxstreet.com/rss/news"
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        for entry in feed.entries[:15]:
            articles.append({
                "title": entry.title,
                "summary": entry.summary,
                "link": entry.link,
                "image": entry.get("media_content", [{}])[0].get("url", None)
            })
        return articles
    except Exception as e:
        if DEBUG_MODE:
            st.write("DEBUG ERROR Forex News:", e)
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
            col3.metric("Most Active", actives.iloc[0]["pair"], f"{actives.iloc[0]['change_percent']}%")

    # Tabs
    tab_movers, tab_charts, tab_news = st.tabs(["📈 Movers", "📉 Charts", "📰 News"])

    # Movers Tab
    with tab_movers:
        st.subheader("🚀 Gainers")
        if not gainers.empty:
            st.dataframe(gainers.style.background_gradient(subset=["change_percent"], cmap="Greens"))
        else:
            st.info("No gainers available.")
        st.subheader("📉 Losers")
        if not losers.empty:
            st.dataframe(losers.style.background_gradient(subset=["change_percent"], cmap="Reds"))
        else:
            st.info("No losers available.")
        st.subheader("🔥 Most Active (Highest Volatility)")
        if not actives.empty:
            st.dataframe(actives.style.background_gradient(subset=["change_percent"], cmap="Blues"))
        else:
            st.info("No active pairs available.")

    # Charts Tab (Snapshot Mode)
    with tab_charts:
        st.subheader("Yesterday's Movers Snapshot")
        if not movers_df.empty:
            st.write("Top 5 Gainers")
            st.bar_chart(gainers.set_index("pair")["change_percent"])

            st.write("Top 5 Losers")
            st.bar_chart(losers.set_index("pair")["change_percent"])

            st.write("Top 5 Most Active (Highest Volatility)")
            st.bar_chart(actives.set_index("pair")["abs_change"])
        else:
            st.info("No data available for yesterday's snapshot.")

    # News Tab
    with tab_news:
        st.subheader("Latest Forex News")
        news = fetch_forex_news()
        if news:
            for article in news[:8]:
                st.markdown("---")
                col1, col2 = st.columns([1,3])
                with col1:
                    if article["image"]:
                        st.image(article["image"], use_container_width=True)
                with col2:
                    st.markdown(f"**{article['title']}**")
                    st.write(article['summary'])
                    st.markdown(f"[🔗 Read more]({article['link']})")
        else:
            st.info("No forex news available.")

if __name__ == "__main__":
    main()











