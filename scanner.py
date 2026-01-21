# scanner_daily_movers_news_predict.py

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# -------------------- CONFIG --------------------
ALPHA_API_KEY = st.secrets["ALPHA_API_KEY"]
POLYGON_API_KEY = st.secrets["POLYGON_API_KEY"]
DEBUG_MODE = st.secrets.get("ADMIN_DEBUG", False)

# -------------------- Alpha Vantage Daily OHLC --------------------
@st.cache_data(ttl=1800)  # cache for 30 minutes
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

# -------------------- Compute Movers --------------------
def compute_daily_movers(watchlist):
    movers = []
    for symbol in watchlist:
        df = fetch_alpha_daily(symbol)
        if not df.empty and len(df) > 1:
            latest = df.iloc[-1]["4. close"]
            prev = df.iloc[-2]["4. close"]
            change_pct = ((latest - prev) / prev) * 100
            volume = df.iloc[-1]["5. volume"]
            movers.append({
                "ticker": symbol,
                "price": round(latest, 2),
                "change_percent": round(change_pct, 2),
                "volume": int(volume)
            })
            if DEBUG_MODE:
                st.write(f"DEBUG {symbol}: price={latest:.2f}, change={change_pct:.2f}%, volume={volume}")
    movers_df = pd.DataFrame(movers)
    if not movers_df.empty:
        gainers = movers_df.sort_values("change_percent", ascending=False).head(5)
        losers = movers_df.sort_values("change_percent", ascending=True).head(5)
        actives = movers_df.sort_values("volume", ascending=False).head(5)
        return gainers, losers, actives
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

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
def score_stock(row, news_keywords):
    score = 0
    if 3 <= row["price"] <= 20:
        score += 1
    if row["change_percent"] >= 30:
        score += 2
    if row["volume"] > 5_000_000:  # proxy for relative volume
        score += 2
    if any(row["ticker"] in kw for kw in news_keywords):
        score += 2
    return score

def generate_predictions(movers_df, news_keywords):
    if movers_df.empty:
        return pd.DataFrame()
    movers_df["score"] = movers_df.apply(lambda r: score_stock(r, news_keywords), axis=1)
    return movers_df.sort_values("score", ascending=False).head(5)

# -------------------- STREAMLIT UI --------------------
def main():
    st.set_page_config(page_title="Daily Movers Scanner", layout="wide")
    st.title("📊 Daily Movers Scanner")
    st.caption("Alpha Vantage daily movers + Polygon news + prediction engine")

    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(f"**Last Updated:** {last_updated}")

    tab_movers, tab_charts, tab_news, tab_predict = st.tabs(
        ["📈 Movers", "📉 Trend Charts", "📰 News", "🔮 Predictions"]
    )

    # Curated universe (expandable)
    watchlist = ["AAPL", "MSFT", "TSLA", "AMZN", "NVDA", "META", "GOOG", "AMD", "NFLX", "INTC"]

    # Compute movers
    gainers, losers, actives = compute_daily_movers(watchlist)

    # Movers Tab
    with tab_movers:
        st.header("Previous Day Movers")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🚀 Gainers")
            if not gainers.empty:
                st.dataframe(gainers, use_container_width=True)
            else:
                st.info("No gainers data available.")
        with col2:
            st.subheader("📉 Losers")
            if not losers.empty:
                st.dataframe(losers, use_container_width=True)
            else:
                st.info("No losers data available.")
        st.subheader("🔥 Most Active")
        if not actives.empty:
            st.dataframe(actives, use_container_width=True)
        else:
            st.info("No active stocks data available.")

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
        if not scored.empty:
            st.dataframe(scored[["ticker", "price", "change_percent", "volume", "score"]], use_container_width=True)
        else:
            st.info("No predictions available.")

if __name__ == "__main__":
    main()







