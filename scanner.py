# scanner_polygon_finnhub_enriched.py

import requests
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# -------------------- CONFIG --------------------
POLYGON_API_KEY = "aZTfdpYgZ0kIAVwdILxPygSHdZ0CrDBu"
FINNHUB_API_KEY = "d5o3171r01qma2b78u4gd5o3171r01qma2b78u50"

# -------------------- POLYGON MOVERS --------------------
def fetch_polygon_movers():
    url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/gainers?apiKey={POLYGON_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "application/json" in response.headers.get("Content-Type", ""):
            return response.json().get("tickers", [])
    except Exception as e:
        print("Error fetching Polygon movers:", e)
    return []

# -------------------- FINNHUB PROFILE --------------------
def fetch_finnhub_profile(symbol):
    url = f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={FINNHUB_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching Finnhub profile for {symbol}:", e)
    return {}

# -------------------- FINNHUB NEWS --------------------
def fetch_finnhub_news():
    """Fetch latest market news from Finnhub.io"""
    url = f"https://finnhub.io/api/v1/news?category=general&token={FINNHUB_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "application/json" in response.headers.get("Content-Type", ""):
            return response.json()
    except Exception as e:
        print("Error fetching Finnhub news:", e)
    return []

# -------------------- SCORING ENGINE --------------------
def score_stocks(movers, vol_thresh, change_thresh, price_min, price_max, float_max):
    scored = []
    for stock in movers:
        symbol = stock.get("ticker")
        price = float(stock.get("lastTrade", {}).get("p", 0))
        change_pct = float(stock.get("todaysChangePerc", 0))
        volume = float(stock.get("day", {}).get("v", 0))
        prev_volume = float(stock.get("prevDay", {}).get("v", 1))

        # Enrich float data from Finnhub
        profile = fetch_finnhub_profile(symbol)
        float_shares = float(profile.get("shareOutstanding", 0))

        volume_ratio = volume / prev_volume if prev_volume > 0 else 0

        # Score each metric (0–1 scale)
        score_vol = min(volume_ratio / vol_thresh, 1)
        score_change = min(change_pct / change_thresh, 1)
        score_price = 1 if price_min <= price <= price_max else 0
        score_float = min(float_max / float_shares, 1) if float_shares > 0 else 0

        match_score = round((score_vol + score_change + score_price + score_float) / 4 * 100, 2)

        scored.append({
            "Symbol": symbol,
            "Price": price,
            "Change (%)": round(change_pct, 2),
            "Volume": volume,
            "Float": int(float_shares),
            "Volume Ratio": round(volume_ratio, 2),
            "Match %": match_score
        })
    return scored

# -------------------- STREAMLIT UI --------------------
def plot_trend(symbol):
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
    st.caption("Powered by Polygon.io (movers) + Finnhub.io (float & news)")

    tab_filters, tab_stocks, tab_analytics, tab_news = st.tabs(["⚙️ Filters", "🚀 Stocks", "📊 Analytics", "📰 News"])

    # Filters Tab
    with tab_filters:
        st.header("Adjust Scanner Criteria")
        vol_thresh = st.slider("Relative Volume (x)", 1, 10, 3)
        change_thresh = st.slider("Daily % Change", 0, 100, 10)
        price_min, price_max = st.slider("Price Range ($)", 1, 500, (1, 50))
        float_max = st.slider("Max Float (shares)", 0, 5_000_000, 5_000_000, step=100_000)

    # Fetch data
    movers = fetch_polygon_movers()
    scored = score_stocks(movers, vol_thresh, change_thresh, price_min, price_max, float_max)
    exact_matches = [s for s in scored if s["Match %"] == 100]
    top_matches = sorted(scored, key=lambda x: x["Match %"], reverse=True)[:10]

    # Stocks Tab
    with tab_stocks:
        st.header("Stocks Meeting Criteria")
        if exact_matches:
            st.markdown(f"**{len(exact_matches)} stocks match all criteria.**")
            for stock in exact_matches:
                with st.container():
                    st.subheader(f"{stock['Symbol']} — ${stock['Price']} ({stock['Change (%)']}%)")
                    st.write(f"📊 Volume Ratio: {stock['Volume Ratio']} | Volume: {stock['Volume']:,} | Float: {stock['Float']:,}")
                    plot_trend(stock['Symbol'])
                    st.divider()
        else:
            st.info("No stocks meet all criteria. Check Analytics tab for near matches.")

    # Analytics Tab
    with tab_analytics:
        st.header("Top 10 Closest Matches")
        df = pd.DataFrame(top_matches)
        st.dataframe(df, use_container_width=True)

    # News Tab
    with tab_news:
        st.header("Latest Market News")
        news = fetch_finnhub_news()
        if news:
            for article in news[:10]:
                with st.expander(article.get("headline", "News Item")):
                    st.write(article.get("summary", ""))
                    url = article.get("url")
                    if url:
                        st.markdown(f"[Read more]({url})")
        else:
            st.info("No news available right now.")

if __name__ == "__main__":
    main()




