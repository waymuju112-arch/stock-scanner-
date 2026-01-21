# scanner.py

import requests
import streamlit as st
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh

# -------------------- CONFIG --------------------
BENZINGA_API_KEY = "bz.WTQQ73ASIU4DILGULR76RAWSOFSRU2XU"
NEWS_API_KEY = "pub_08ee44a47dff4904afbb1f82899a98d7"  

# -------------------- BENZINGA DATA FETCH --------------------
def fetch_market_data():
    """Fetch movers from Benzinga (top gainers, losers, volume leaders)."""
    url = f"https://api.benzinga.com/api/v2.1/calendar/movers?token={BENZINGA_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "application/json" in response.headers.get("Content-Type", ""):
            return response.json().get("movers", [])
    except Exception:
        return []
    return []

def fetch_benzinga_news():
    """Fetch latest market news headlines from Benzinga safely."""
    url = f"https://api.benzinga.com/api/v2/news?token={BENZINGA_API_KEY}&channels=markets&limit=10"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "application/json" in response.headers.get("Content-Type", ""):
            data = response.json()
            if data:
                return data
    except Exception:
        return []
    return []

def fetch_news_fallback():
    """Fallback to NewsAPI.org if Benzinga returns nothing or invalid JSON."""
    url = f"https://newsapi.org/v2/top-headlines?category=business&apiKey={NEWS_API_KEY}&pageSize=10"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "application/json" in response.headers.get("Content-Type", ""):
            return response.json().get("articles", [])
    except Exception:
        return []
    return []

# -------------------- FILTER ENGINE --------------------
def filter_stocks(movers, vol_ratio_thresh, change_thresh, price_min, price_max, float_max):
    """Apply adjustable criteria to Benzinga movers."""
    filtered = []
    for stock in movers:
        symbol = stock.get("ticker")
        price = float(stock.get("price", 0))
        change_pct = float(stock.get("change_percent", 0))
        volume = float(stock.get("volume", 0))
        avg_volume = float(stock.get("avg_volume", 1))
        float_shares = float(stock.get("float", 0))

        volume_ratio = volume / avg_volume if avg_volume > 0 else 0

        if (volume_ratio >= vol_ratio_thresh and
            change_pct >= change_thresh and
            price_min <= price <= price_max and
            float_shares <= float_max):
            filtered.append({
                "Symbol": symbol,
                "Price": price,
                "Change (%)": change_pct,
                "Volume Ratio": round(volume_ratio, 2),
                "Float": float_shares
            })
    return filtered

# -------------------- STREAMLIT UI --------------------
def plot_trend(symbol):
    """Placeholder trend chart (Benzinga free tier doesn’t provide historical candles)."""
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
    - Demand: Relative Volume threshold (adjustable)  
    - Demand: % Change threshold (adjustable)  
    - Demand: Price range (adjustable)  
    - Supply: Float max (adjustable)  
    """)

def main():
    st.set_page_config(page_title="Tadi's Benzinga Scanner", layout="wide")

    # Auto-refresh every 60 seconds
    st_autorefresh(interval=60000, limit=None, key="refresh")

    st.title("📈 Tadi's Scanner — Full Market Edge")
    st.subheader("Real-time Benzinga data with adjustable filters")

    col1, col2, col3 = st.columns([1, 2, 1])

    # Left: Criteria + Sliders
    with col1:
        show_criteria()
        st.markdown("### 🔧 Adjust Filters")
        vol_ratio_thresh = st.slider("Relative Volume (x)", 1, 10, 5)
        change_thresh = st.slider("Daily % Change", 0, 100, 30)
        price_min, price_max = st.slider("Price Range ($)", 1, 50, (3, 20))
        float_max = st.slider("Max Float (shares)", 1_000_000, 50_000_000, 5_000_000, step=1_000_000)

    # Middle: Filtered Stocks
    with col2:
        st.markdown("### 🚀 Stocks Meeting Criteria")
        movers = fetch_market_data()
        filtered = filter_stocks(movers, vol_ratio_thresh, change_thresh, price_min, price_max, float_max)

        if filtered:
            for stock in filtered:
                st.markdown(f"#### {stock['Symbol']} — ${stock['Price']} ({stock['Change (%)']}%)")
                st.write(f"📊 Volume Ratio: {stock['Volume Ratio']} | 🧮 Float: {stock['Float']:,}")
                plot_trend(stock['Symbol'])
                st.markdown("---")
        else:
            st.warning("No stocks currently meet all criteria.")

    # Right: Market News
    with col3:
        st.markdown("### 📰 Latest Market News")
        news = fetch_benzinga_news()
        if not news:
            news = fetch_news_fallback()

        if news:
            for article in news:
                title = article.get("title") or article.get("headline")
                url = article.get("url")
                st.write(f"**{title}**")
                if url:
                    st.caption(url)
        else:
            st.info("No news available right now.")

if __name__ == "__main__":
    main()




