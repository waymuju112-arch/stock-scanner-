# scanner_ui_refactor_emojis.py

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
    """Apply filters to Polygon movers."""
    filtered = []
    for stock in movers:
        symbol = stock.get("ticker")
        price = float(stock.get("lastTrade", {}).get("p", 0))
        change_pct = float(stock.get("todaysChangePerc", 0))
        volume = float(stock.get("day", {}).get("v", 0))
        prev_volume = float(stock.get("prevDay", {}).get("v", 1))
        float_shares = float(stock.get("sharesOutstanding", 0))

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
    plt.plot([1, 2, 3, 4, 5], [10, 12, 15, 14, 18], marker="o", color="blue")
    plt.title(f"{symbol} Trend Projection")
    plt.xlabel("Days")
    plt.ylabel("Price")
    st.pyplot(plt)

def main():
    st.set_page_config(page_title="Tadi's Market Scanner", layout="wide")

    # Auto-refresh every 60 seconds
    st_autorefresh(interval=60000, limit=None, key="refresh")

    st.title("📈 Tadi's Market Scanner")
    st.caption("Powered by Polygon.io (movers) and Finnhub.io (news)")

    # Tabs for cleaner navigation
    tab_filters, tab_stocks, tab_news = st.tabs(["⚙️ Filters", "🚀 Stocks", "📰 News"])

    # Filters Tab
    with tab_filters:
        st.header("Adjust Scanner Criteria")
        vol_ratio_thresh = st.slider("Relative Volume (x)", 1, 10, 3)
        change_thresh = st.slider("Daily % Change", 0, 100, 10)
        price_min, price_max = st.slider("Price Range ($)", 1, 500, (1, 50))
        float_max = st.slider("Max Float (shares)", 0, 5_000_000, 5_000_000, step=100_000)

    # Stocks Tab
    with tab_stocks:
        st.header("Stocks Meeting Criteria")
        movers = fetch_polygon_movers()
        filtered = filter_stocks(movers, vol_ratio_thresh, change_thresh, price_min, price_max, float_max)

        if filtered:
            st.markdown(f"**{len(filtered)} stocks currently meet your criteria.**")
            for stock in filtered:
                with st.container():
                    st.subheader(f"{stock['Symbol']} — ${stock['Price']} ({stock['Change (%)']}%)")
                    st.write(f"📊 Volume Ratio: {stock['Volume Ratio']} | Volume: {stock['Volume']:,} | Float: {stock['Float']:,}")
                    plot_trend(stock['Symbol'])
                    st.divider()
        else:
            st.info("No stocks currently meet the criteria.")

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

