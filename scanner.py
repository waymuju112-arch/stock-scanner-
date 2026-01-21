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

# -------------------- YAHOO FINANCE TOP GAINERS --------------------
def fetch_top_gainers(limit=100):
    """Fetch top gainers using Yahoo Finance (yfinance)"""
    try:
        gainers = yf.get_day_gainers().head(limit)
        return gainers
    except Exception as e:
        print("Error fetching Yahoo Finance gainers:", e)
    return pd.DataFrame()

# -------------------- STREAMLIT UI --------------------
def plot_trend(symbol):
    """Simple placeholder trend chart"""
    plt.figure(figsize=(6, 3))
    plt.plot([1, 2, 3, 4, 5], [10, 12, 15, 14, 18], marker="o", color="blue")
    plt.title(f"{symbol} Trend Projection")
    plt.xlabel("Days")
    plt.ylabel("Price")
    st.pyplot(plt)

def main():
    st.set_page_config(page_title="Tadi's Market Scanner", layout="wide")
    st_autorefresh(interval=60000, limit=None, key="refresh")

    st.title("📈 Tadi's Market Scanner")
    st.caption("Powered by Yahoo Finance (top gainers) + Polygon.io (news)")

    tab_stocks, tab_analytics, tab_news = st.tabs(["🚀 Stocks", "📊 Analytics", "📰 News"])

    # Fetch data
    gainers = fetch_top_gainers(limit=100)

    # Stocks Tab
    with tab_stocks:
        st.header("Top 100 Performing Stocks (Gainers)")
        if not gainers.empty:
            for _, row in gainers.iterrows():
                with st.container():
                    st.subheader(f"{row['Symbol']} — ${row['Price']} ({row['% Change']}%)")
                    st.write(f"📊 Volume: {row['Volume']:,} | Market Cap: {row['Market Cap']}")
                    plot_trend(row['Symbol'])
                    st.divider()
        else:
            st.info("No stock data available right now.")

    # Analytics Tab
    with tab_analytics:
        st.header("Analytics: Top Gainers Overview")
        if not gainers.empty:
            st.dataframe(gainers, use_container_width=True)
            # Chart top 10 by % change
            top10 = gainers.head(10)
            st.bar_chart(top10.set_index("Symbol")["% Change"])
        else:
            st.info("No analytics available right now.")

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



