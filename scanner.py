# scanner_polygon_finnhub_float.py

import requests
import streamlit as st
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh

# -------------------- CONFIG --------------------
POLYGON_API_KEY = "aZTfdpYgZ0kIAVwdILxPygSHdZ0CrDBu"
FINNHUB_API_KEY = "d5o3171r01qma2b78u4gd5o3171r01qma2b78u50"

# -------------------- POLYGON MOVERS --------------------
def fetch_polygon_movers():
    """Fetch top gainers/losers from Polygon.io"""
    url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/gainers?apiKey={POLYGON_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "application/json" in response.headers.get("Content-Type", ""):
            return response.json().get("tickers", [])
        else:
            print("Polygon movers raw response:", response.text[:200])
    except Exception as e:
        print("Error fetching Polygon movers:", e)
    return []

# -------------------- FINNHUB NEWS --------------------
def fetch_finnhub_news():
    """Fetch latest market news from Finnhub.io"""
    url = f"https://finnhub.io/api/v1/news?category=general&token={FINNHUB_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "application/json" in response.headers.get("Content-Type", ""):
            return response.json()
        else:
            print("Finnhub news raw response:", response.text[:200])
    except Exception as e:
        print("Error fetching Finnhub news:", e)
    return []

# -------------------- FILTER ENGINE --------------------
def filter_stocks(movers, vol_ratio_thresh, change_thresh, price_min, price_max, float_max):
    """Apply Warrior Trading-style filters to Polygon movers."""
    filtered = []
    for stock in movers:
        symbol = stock.get("ticker")
        price = float(stock.get("lastTrade", {}).get("p", 0))
        change_pct = float(stock.get("todaysChangePerc", 0))
        volume = float(stock.get("day", {}).get("v", 0))
        prev_volume = float(stock.get("prevDay", {}).get("v", 1))
        float_shares = float(stock.get("sharesOutstanding", 0))  # supply/float

        volume_ratio = volume / prev_volume if prev_volume > 0 else 0

        if (volume_ratio >= vol_ratio_thresh and
            change_pct >= change_thresh and
            price_min <= price <= price_max and
            float_shares <= float_max):
            filtered.append({
                "Symbol": symbol,
                "Price": price,
                "Change (%)": round(change_pct, 2),
                "Volume Ratio": round(volume_ratio, 2),
                "Volume": volume,
                "Float": int(float_shares)
            })
    return filtered

# -------------------- STREAMLIT UI --------------------
def plot_trend(symbol):
    """Placeholder trend chart."""
    plt.figure(figsize=(6, 3))
    plt.plot([1, 2, 3, 4, 5], [10, 12, 15, 14, 18], marker="o", color="green")
    plt.title(f"{symbol} Trend Projection")
    plt.xlabel("Days")
    plt.ylabel("Price")
    st.pyplot(plt)

def show_criteria():
    st.markdown("### 📋 Scanner Criteria")
    st.markdown("""
    **Indicators of High Demand and Low Supply**
    - Relative Volume threshold (adjustable)  
    - % Change threshold (adjustable)  
    - Price range (adjustable)  
    - Supply: Float max (adjustable, capped at 5M)  
    """)

def main():
    st.set_page_config(page_title="Tadi's Polygon/Finnhub Scanner", layout="wide")

    # Auto-refresh every 60 seconds
    st_autorefresh(interval=60000, limit=None, key="refresh")

    st.title("📈 Tadi's Scanner — Polygon Movers + Finnhub News")
    st.subheader("Real-time market data")

    col1, col2, col3 = st.columns([1, 2, 1])

    # Left: Filters
    with col1:
        show_criteria()
        st.markdown("### 🔧 Adjust Filters")
        vol_ratio_thresh = st.slider("Relative Volume (x)", 1, 10, 3)
        change_thresh = st.slider("Daily % Change", 0, 100, 10)
        price_min, price_max = st.slider("Price Range ($)", 1, 500, (1, 50))
        float_max = st.slider("Max Float (shares)", 0, 5_000_000, 5_000_000, step=100_000)

    # Middle: Filtered Stocks
    with col2:
        st.markdown("### 🚀 Stocks Meeting Criteria")
        movers = fetch_polygon_movers()
        filtered = filter_stocks(movers, vol_ratio_thresh, change_thresh, price_min, price_max, float_max)

        if filtered:
            for stock in filtered:
                st.markdown(f"#### {stock['Symbol']} — ${stock['Price']} ({stock['Change (%)']}%)")
                st.write(f"📊 Volume Ratio: {stock['Volume Ratio']} | Volume: {stock['Volume']:,} | Float: {stock['Float']:,}")
                plot_trend(stock['Symbol'])
                st.markdown("---")
        else:
            st.warning("No stocks currently meet all criteria.")

    # Right: Market News
    with col3:
        st.markdown("### 📰 Latest Market News")
        news = fetch_finnhub_news()

        if news:
            for article in news[:10]:
                title = article.get("headline") or article.get("summary")
                url = article.get("url")
                st.write(f"**{title}**")
                if url:
                    st.caption(url)
        else:
            st.info("No news available right now.")

if __name__ == "__main__":
    main()


