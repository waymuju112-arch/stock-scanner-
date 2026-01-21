# scanner_marketwide_predict.py

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# -------------------- CONFIG --------------------
ALPHA_API_KEY = st.secrets["ALPHA_API_KEY"]
POLYGON_API_KEY = st.secrets["POLYGON_API_KEY"]
DEBUG_MODE = st.secrets.get("ADMIN_DEBUG", False)

# -------------------- Load Universe --------------------
@st.cache_data(ttl=3600)
def load_universe():
    # For prototype: static list of major tickers (S&P 500 subset)
    return ["AAPL","MSFT","TSLA","AMZN","NVDA","META","GOOG","AMD","NFLX","INTC","BA","DIS","PYPL","SQ","SHOP"]

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
    for symbol in universe:
        df = fetch_alpha_daily(symbol)
        if not df.empty and len(df) > 20:
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
            if DEBUG_MODE:
                st.write(f"DEBUG {symbol}: price={latest['4. close']:.2f}, change={change_pct:.2f}%, rel_vol={rel_vol:.2f}")
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

# -------------------- Prediction Engine --------------------
def score_stock(row, news_keywords):
    score = 0
    if 3 <= row["price"] <= 20:
        score += 1
    if row["change_percent"] >= 30:
        score += 2
    if row["relative_volume"] >= 5:
        score += 2
    if any(row["ticker"] in kw for kw in news_keywords):
        score += 2
    # Float < 5M requires external dataset; placeholder logic
    if row["volume"] < 5_000_000:  # proxy for low float
        score += 1
    return score

def generate_predictions(movers_df, news_keywords):
    if movers_df.empty:
        return pd.DataFrame()
    movers_df["score"] = movers_df.apply(lambda r: score_stock(r, news_keywords), axis=1)
    return movers_df.sort_values("score", ascending=False).head(10)

# -------------------- STREAMLIT UI --------------------
def main():
    st.set_page_config(page_title="Market-Wide Scanner", layout="wide")
    st.title("📊 Market-Wide Demand/Supply Scanner")
    st.caption("Daily movers + hourly charts + news thumbnails + prediction engine")

    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(f"**Last Updated:** {last_updated}")

    tab_movers, tab_charts, tab_news, tab_predict = st.tabs(
        ["📈 Movers", "📉 Hourly Charts", "📰 News", "🔮 Predictions"]
    )

    # Universe
    universe = load_universe()

    # Compute movers
    gainers, losers, actives, movers_df = compute_daily_movers(universe)

    # Movers Tab
    with tab_movers:
        st.header("Previous Day Movers")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🚀 Gainers")
            st.dataframe(gainers, use_container_width=True)
        with col2:
            st.subheader("📉 Losers")
            st.dataframe(losers, use_container_width=True)
        st.subheader("🔥 Most Active")
        st.dataframe(actives, use_container_width=True)

    # Charts Tab
    with tab_charts:
        st.header("Hourly Bar Chart (Previous Day)")
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
        st.header("Latest Market News")
        news = fetch_polygon_news()
        if news:
            for article in news[:10]:
                with st.expander(article.get("title", "News Item")):
                    image_url = article.get("image_url")
                    if image_url:
                        st.image(image_url, width=150)
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
        scored = generate_predictions(movers_df, news_keywords)
        st.dataframe(scored[["ticker","price","change_percent","volume","relative_volume","score"]], use_container_width=True)

if __name__ == "__main__":
    main()








