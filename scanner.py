# scanner_yfinance_polygon_news.py

import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
import requests
from streamlit_autorefresh import st_autorefresh

# -------------------- CONFIG --------------------
POLYGON_API_KEY = "aZTfdpYgZ0kIAVwdILxPygSHdZ0CrDBu"

# -------------------- POLYGON NEWS --------------------
def fetch_polygon_news():
    """Fetch latest market news from Polygon.io"""
    url = f"https://api.polygon.io/v2/reference/news?apiKey={POLYGON_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "application/json" in response.headers.get("Content-Type", ""):
            return response.json().get("results", [])
    except Exception as e:
        print("Error fetching Polygon news:", e)
    return []

# -------------------- YAHOO FINANCE MOVERS --------------------
def fetch_top_gainers(limit=100):
    """Fetch top gainers using Yahoo Finance"""
    try:
        gainers = yf.get_day_gainers().head(limit)
        return gainers
    except Exception as e:
        print("Error fetching Yahoo Finance gainers:", e)
    return pd.DataFrame()

def fetch_top_losers(limit=100):
    """Fetch top losers using Yahoo Finance"""
    try:
        losers = yf.get_day_losers().head(limit)
        return losers
    except Exception as e:
        print("Error fetching Yahoo Finance losers:", e)
    return pd.DataFrame()

# -------------------- SCORING ENGINE --------------------
def score_stocks(df):
    """Apply grading mechanism to movers"""
    scored = []
    for _, row in df.iterrows():
        symbol = row["Symbol"]
        price = row["Price"]
        change_pct = row["% Change"]
        volume = row["Volume"]

        # Score: normalize % change and volume
        score_change = min(abs(change_pct) / 10, 1)  # scale % change
        score_volume = min(volume / 1_000_000, 1)   # scale volume

        # Weighted score
        match_score = round((score_change*0.6 + score_volume*0.4) * 100, 2)

        scored.append({
            "Symbol": symbol,
            "Price": price,
            "Change (%)": change_pct,
            "Volume": volume,
            "Match %": match_score
        })
    return scored

# -------------------- STREAMLIT UI --------------------
def main():
    st.set_page_config(page_title="Tadi's Market Scanner", layout="wide")
    st_autorefresh(interval=60000, limit=None, key="refresh")

    st.title("📈 Tadi's Market Scanner")
    st.caption("Powered by Yahoo Finance (gainers & losers) + Polygon.io (news)")

    tab_movers, tab_news = st.tabs(["📊 Market Movers", "📰 News"])

    # Fetch data
    gainers = fetch_top_gainers(limit=100)
    losers = fetch_top_losers(limit=100)

    scored_gainers = score_stocks(gainers) if not gainers.empty else []
    scored_losers = score_stocks(losers) if not losers.empty else []

    # Market Movers Tab
    with tab_movers:
        st.header("Top Market Movers")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🚀 Top 100 Gainers")
            if scored_gainers:
                df_gainers = pd.DataFrame(scored_gainers)
                st.dataframe(df_gainers, use_container_width=True)
                st.bar_chart(df_gainers.set_index("Symbol")["Match %"].head(10))
            else:
                st.info("No gainers data available right now.")

        with col2:
            st.subheader("📉 Top 100 Losers")
            if scored_losers:
                df_losers = pd.DataFrame(scored_losers)
                st.dataframe(df_losers, use_container_width=True)
                st.bar_chart(df_losers.set_index("Symbol")["Match %"].head(10))
            else:
                st.info("No losers data available right now.")

    # News Tab
    with tab_news:
        st.header("Latest Market News")
        news = fetch_polygon_news()
        if news:
            for article in news[:10]:
                with st.expander(article.get("title", "News Item")):
                    # Thumbnail image if available
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


