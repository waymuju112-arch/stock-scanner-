# scanner_sp500_sidebar_safe.py

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
    df = pd.read_csv("sp500.csv")
    return df["Symbol"].dropna().unique().tolist()

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
    return pd.DataFrame(movers)

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
    if row["volume"] < 5_000_000:  # proxy for low float
        score += 1
    return score

def generate_predictions(movers_df, news_keywords):
    if movers_df.empty:
        # Always return consistent columns
        return pd.DataFrame(columns=["ticker","price","change_percent","volume","relative_volume","score"])
    movers_df = movers_df.copy()
    movers_df["score"] = movers_df.apply(lambda r: score_stock(r, news_keywords), axis=1)
    return movers_df.sort_values("score", ascending=False).head(10)

# -------------------- STREAMLIT UI --------------------
def main():
    st.set_page_config(page_title="S&P 500 Dashboard", layout="wide")
    st.title("📊 S&P 500 Demand/Supply Dashboard")

    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Last Updated: {last_updated}")

    # Sidebar filter panel
    st.sidebar.header("⚙️ Warrior Trading Criteria")
    min_rel_vol = st.sidebar.slider("Relative Volume ≥", 1, 10, 5)
    min_change = st.sidebar.slider("Percent Change ≥", 0, 100, 30)
    price_range = st.sidebar.slider("Price Range ($)", 1, 100, (3, 20))
    max_float_proxy = st.sidebar.slider("Max Volume (proxy for float)", 1_000_000, 50_000_000, 5_000_000)

    # Universe
    universe = load_sp500_universe()
    movers_df = compute_daily_movers(universe)

    # Apply filters
    filtered = movers_df[
        (movers_df["relative_volume"] >= min_rel_vol) &
        (movers_df["change_percent"] >= min_change) &
        (movers_df["price"].between(price_range[0], price_range[1])) &
        (movers_df["volume"] <= max_float_proxy)
    ]

    # Quick Metrics
    if not movers_df.empty:
        gainers = movers_df.sort_values("change_percent", ascending=False).head(10)
        losers = movers_df.sort_values("change_percent", ascending=True).head(10)
        actives = movers_df.sort_values("volume", ascending=False).head(10)

        col1, col2, col3 = st.columns(3)
        col1.metric("Top Gainer", gainers.iloc[0]["ticker"], f"{gainers.iloc[0]['change_percent']}%")
        col2.metric("Top Loser", losers.iloc[0]["ticker"], f"{losers.iloc[0]['change_percent']}%")
        col3.metric("Most Active", actives.iloc[0]["ticker"], f"{actives.iloc[0]['volume']:,}")

    # Tabs
    tab_movers, tab_charts, tab_news, tab_predict = st.tabs(
        ["📈 Movers", "📉 Charts", "📰 News", "🔮 Predictions"]
    )

    # Movers Tab
    with tab_movers:
        st.subheader("Filtered Market Movers")
        if not filtered.empty:
            st.dataframe(filtered.style.background_gradient(subset=["change_percent"], cmap="RdYlGn"))
        else:
            st.info("No movers match your current filter criteria.")

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
        st.subheader("Prediction Engine")
        news_keywords = [article.get("title", "") for article in fetch_polygon_news()]
        scored = generate_predictions(filtered, news_keywords)
        if not scored.empty and "score" in scored.columns:
            st.dataframe(scored.style.background_gradient(subset=["score"], cmap="Blues"))
        else:
            st.info("No predictions available with current filters.")

if __name__ == "__main__":
    main()












