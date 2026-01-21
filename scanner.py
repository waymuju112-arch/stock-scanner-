import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import matplotlib.pyplot as plt

POLYGON_API_KEY = "aZTfdpYgZ0kIAVwdILxPygSHdZ0CrDBu"
ALPHA_API_KEY = "HV1L0BLBFPRE2FYQ"
FINNHUB_API_KEY = "d5o3171r01qma2b78u4gd5o3171r01qma2b78u50"

# Polygon News
def fetch_polygon_news():
    url = f"https://api.polygon.io/v2/reference/news?apiKey={POLYGON_API_KEY}"
    r = requests.get(url)
    if r.status_code == 200:
        return r.json().get("results", [])
    return []

# Yahoo Finance Movers
def fetch_gainers(limit=100):
    return yf.get_day_gainers().head(limit)

def fetch_losers(limit=100):
    return yf.get_day_losers().head(limit)

def fetch_most_active(limit=100):
    return yf.get_day_most_active().head(limit)

# Alpha Vantage OHLC
def fetch_alpha_daily(symbol):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={ALPHA_API_KEY}"
    r = requests.get(url)
    if r.status_code == 200:
        return r.json().get("Time Series (Daily)", {})
    return {}

# Finnhub Quote
def fetch_finnhub_quote(symbol):
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    return {}

# Streamlit UI
def main():
    st.set_page_config(page_title="Tadi's Market Scanner", layout="wide")
    st.title("📈 Tadi's Market Scanner")

    tab_movers, tab_charts, tab_news = st.tabs(["📊 Market Movers", "📈 Charts", "📰 News"])

    # Movers Tab
    with tab_movers:
        col1, col2 = st.columns(2)
        gainers = fetch_gainers()
        losers = fetch_losers()
        if not gainers.empty:
            col1.subheader("🚀 Gainers")
            col1.dataframe(gainers)
        if not losers.empty:
            col2.subheader("📉 Losers")
            col2.dataframe(losers)

    # Charts Tab
    with tab_charts:
        st.subheader("Market Sentiment")
        sizes = [len(fetch_gainers()), len(fetch_losers())]
        labels = ["Gainers", "Losers"]
        colors = ["green", "red"]
        fig1, ax1 = plt.subplots()
        ax1.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%")
        st.pyplot(fig1)

        st.subheader("Example Line Chart (AAPL)")
        data = fetch_alpha_daily("AAPL")
        if data:
            df = pd.DataFrame.from_dict(data, orient="index").astype(float)
            df.index = pd.to_datetime(df.index)
            st.line_chart(df["4. close"].sort_index())

    # News Tab
    with tab_news:
        st.subheader("Latest Market News")
        news = fetch_polygon_news()
        for article in news[:10]:
            with st.expander(article.get("title", "News Item")):
                if article.get("image_url"):
                    st.image(article["image_url"], width=200)
                st.write(article.get("description", ""))
                if article.get("article_url"):
                    st.markdown(f"[Read more]({article['article_url']})")

if __name__ == "__main__":
    main()



