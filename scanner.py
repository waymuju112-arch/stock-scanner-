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

# -------------------- SCORING ENGINE --------------------
def score_stocks(movers, vol_thresh, change_thresh, price_min, price_max, float_max):
    scored = []
    for stock in movers:
        symbol = stock.get("ticker")
        price = float(stock.get("lastTrade", {}).get("p", 0))
        change_pct = float(stock.get("todaysChangePerc", 0))
        volume = float(stock.get("day", {}).get("v", 0))
        prev_volume = float(stock.get("prevDay", {}).get("v", 1))

        # Enrich float data from Finnhub (fallback to 1 if missing)
        profile = fetch_finnhub_profile(symbol)
        float_shares = float(profile.get("shareOutstanding", 1))

        volume_ratio = volume / prev_volume if prev_volume > 0 else 0

        # Weighted scoring (volume + change are most important)
        score_vol = min(volume_ratio / vol_thresh, 1)
        score_change = min(change_pct / change_thresh, 1)
        score_price = 1 if price_min <= price <= price_max else 0
        score_float = min(float_max / float_shares, 1)

        # Weighted average: 40% volume, 40% change, 10% price, 10% float
        match_score = round((score_vol*0.4 + score_change*0.4 + score_price*0.1 + score_float*0.1) * 100, 2)

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
    st.caption("Powered by Polygon.io (movers + news) + Finnhub.io (float data)")

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
    near_misses = [s for s in scored if 80 <= s["Match %"] < 100]
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
            st.info("No stocks meet all criteria.")

        # Near Misses Section
        if near_misses:
            st.subheader("⚡ Near Misses (80–99% Match)")
            for stock in near_misses:
                with st.container():
                    st.write(f"{stock['Symbol']} — {stock['Match %']}% match | Price: ${stock['Price']} | Change: {stock['Change (%)']}%")
                    st.write(f"Volume Ratio: {stock['Volume Ratio']} | Volume: {stock['Volume']:,} | Float: {stock['Float']:,}")
                    st.divider()

    # Analytics Tab
    with tab_analytics:
        st.header("Top 10 Closest Matches")
        df = pd.DataFrame(top_matches)
        st.dataframe(df, use_container_width=True)

    # News Tab
    with tab_news:
        st.header("Latest Market News")
        news = fetch_polygon_news()
        if news:
            for article in news[:10]:
                with st.expander(article.get("title", "News Item")):
                    st.write(article.get("description", ""))
                    url = article.get("url")
                    if url:
                        st.markdown(f"[Read more]({url})")
        else:
            st.info("No news available right now.")

if __name__ == "__main__":
    main()



