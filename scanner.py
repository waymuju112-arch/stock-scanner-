# scanner_snapshot_trend_news_predict.py

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# -------------------- CONFIG --------------------
ALPHA_API_KEY = st.secrets["ALPHA_API_KEY"]
POLYGON_API_KEY = st.secrets["POLYGON_API_KEY"]
DEBUG_MODE = st.secrets.get("ADMIN_DEBUG", False)

# -------------------- Snapshot Movers (Massive API or fallback) --------------------
@st.cache_data(ttl=900)
def fetch_snapshot_movers(direction="gainers"):
    url = f"https://api.marketdataapi.com/v2/snapshot/locale/us/markets/stocks/{direction}?apikey={POLYGON_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if DEBUG_MODE:
            st.write(f"DEBUG Snapshot {direction}:", r.status_code)
            st.json(r.json())
        if r.status_code == 200:
            return pd.DataFrame(r.json().get("tickers", []))
    except Exception as e:
        if DEBUG_MODE:
            st.write(f"DEBUG ERROR Snapshot {direction}:", e)
    return pd.DataFrame()

# -------------------- Alpha Vantage Daily OHLC --------------------
@st.cache_data(ttl=1800)
def fetch_alpha_daily(symbol):
    url = (
        f"https://www.alphavantage.co/query?"
        f"function=TIME_SERIES_DAILY&symbol={symbol}&apikey={ALPHA_API_KEY}&outputsize=compact"
    )
    try:
        r = requests.get(url, timeout=10)
        if DEBUG_MODE:
            st.write(f"DEBUG Alpha Daily {symbol}:", r.status_code)
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

# -------------------- Polygon News --------------------
@st.cache_data(ttl=900)
def fetch_polygon_news():
    url = f"https://api.polygon.io/v2/reference/news?apiKey={POLYGON_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if DEBUG_MODE:
            st.write("DEBUG Polygon News:", r.status_code)
        if r.status_code == 200:
            return r.json().get("results", [])
    except Exception as e:
        if DEBUG_MODE:
            st.write("DEBUG ERROR Polygon News:", e)
    return []

# -------------------- Prediction Engine --------------------
def score_stock(row):
    score = 0
    if row.get("price", 0) >= 3 and row.get("price", 0) <= 20:
        score += 1
    if row.get("change_percent", 0) >= 30:
        score += 2
    if row.get("volume", 0) > row.get("avg_volume", 0) * 5:
        score += 2
    if row.get("news_catalyst", False):
        score += 2
    return score

def generate_predictions(movers_df, news_keywords):
    movers_df["news_catalyst"] = movers_df["ticker"].apply(
        lambda x: any(x in kw for kw in news_keywords)
    )
    movers_df["score"] = movers_df.apply(score_stock, axis=1)
    return movers_df.sort_values("score", ascending=False).head(5)

# -------------------- STREAMLIT UI --------------------
def main():
    st.set_page_config(page_title="Snapshot Scanner", layout="wide")
    st.title("📊 Snapshot Market Scanner")
    st.caption("Previous day movers + trend charts + news catalysts + prediction engine")

    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(f"**Last Updated:** {last_updated}")

    tab_movers, tab_charts, tab_news, tab_predict = st.tabs(
        ["📈 Snapshot Movers", "📉 Trend Charts", "📰 News", "🔮 Predictions"]
    )

    # Fetch snapshot movers
    gainers = fetch_snapshot_movers("gainers")
    losers = fetch_snapshot_movers("losers")
    actives = fetch_snapshot_movers("actives")

    # Movers Tab
    with tab_movers:
        st.header("Previous Day Movers")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🚀 Gainers")
            st.dataframe(gainers[["ticker", "price", "change_percent", "volume"]], use_container_width=True)
        with col2:
            st.subheader("📉 Losers")
            st.dataframe(losers[["ticker", "price", "change_percent", "volume"]], use_container_width=True)
        st.subheader("🔥 Most Active")
        st.dataframe(actives[["ticker", "price", "volume"]], use_container_width=True)

    # Charts Tab
    with tab_charts:
        st.header("Trend Chart")
        symbol = st.text_input("Enter a ticker to chart:", "AAPL")
        df = fetch_alpha_daily(symbol)
        if not df.empty:
            st.line_chart(df["4. close"])
        else:
            st.info(f"No daily data available for {symbol}.")

    # News Tab
    with tab_news:
        st.header("Latest Market News")
        news = fetch_polygon_news()
        if news:
            for article in news[:10]:
                with st.expander(article.get("title", "News Item")):
                    st.write(article.get("description", ""))
                    url = article.get("article_url")
                    if url:
                        st.markdown(f"[Read more]({url})")
        else:
            st.info("No news available.")

    # Prediction Tab
    with tab_predict:
        st.header("Prediction Engine")
        news_keywords = [article.get("title", "") for article in fetch_polygon_news()]
        scored = generate_predictions(gainers, news_keywords)
        st.dataframe(scored[["ticker", "price", "change_percent", "volume", "score"]], use_container_width=True)

if __name__ == "__main__":
    main()








