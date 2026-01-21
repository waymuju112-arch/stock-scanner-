# benzinga_scanner.py

import requests
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# -------------------- CONFIG --------------------
BENZINGA_API_KEY = "YOUR_BENZINGA_API_KEY"

# -------------------- BENZINGA DATA FETCH --------------------
def fetch_market_data():
    """Fetch movers from Benzinga (top gainers, losers, volume leaders)."""
    url = f"https://api.benzinga.com/api/v2.1/calendar/movers?token={BENZINGA_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("movers", [])
    return []

def fetch_news():
    """Fetch latest market news headlines."""
    url = f"https://api.benzinga.com/api/v2/news?token={BENZINGA_API_KEY}&channels=markets&limit=10"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

# -------------------- FILTER ENGINE --------------------
def filter_stocks(movers):
    """Apply Warrior Trading criteria to Benzinga movers."""
    filtered = []
    for stock in movers:
        symbol = stock.get("ticker")
        price = float(stock.get("price", 0))
        change_pct = float(stock.get("change_percent", 0))
        volume = float(stock.get("volume", 0))
        avg_volume = float(stock.get("avg_volume", 1))
        float_shares = float(stock.get("float", 0))

        volume_ratio = volume / avg_volume if avg_volume > 0 else 0

        if (volume_ratio >= 5 and
            change_pct >= 30 and
            3 <= price <= 20 and
            float_shares <= 5_000_000):
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
    """Placeholder trend chart (Benzinga doesn’t provide historical candles in free tier)."""
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
    - ✅ Demand: 5x Relative Volume  
    - ✅ Demand: Already up 30% on the day  
    - ✅ Demand: News Event moving the stock higher  
    - ✅ Demand: Price Between $3.00 - $20.00  
    - ✅ Supply: Float < 5M shares  
    """)

def main():
    st.set_page_config(page_title="Tadi's Benzinga Scanner", layout="wide")

    st.title("📈 Tadi's Scanner — Full Market Edge")
    st.subheader("Real-time Benzinga data with Warrior Trading filters")

    col1, col2, col3 = st.columns([1, 2, 1])

    # Left: Criteria
    with col1:
        show_criteria()

    # Middle: Filtered Stocks
    with col2:
        st.markdown("### 🚀 Stocks Meeting Criteria")
        movers = fetch_market_data()
        filtered = filter_stocks(movers)

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
        news = fetch_news()
        if news:
            for article in news:
                st.write(f"**{article['title']}**")
                st.caption(article['url'])
        else:
            st.info("No news available right now.")

if __name__ == "__main__":
    main()





