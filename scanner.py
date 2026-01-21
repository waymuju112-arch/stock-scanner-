# scanner_watchlist.py

import requests
import streamlit as st
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh

# -------------------- CONFIG --------------------
BENZINGA_API_KEY = "bz.WTQQ73ASIU4DILGULR76RAWSOFSRU2XU"
NEWS_API_KEY = "pub_08ee44a47dff4904afbb1f82899a98d7"  # optional fallback
WATCHLIST = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN"]  # customize your tickers

# -------------------- BENZINGA QUOTES --------------------
def fetch_quotes(tickers):
    url = f"https://api.benzinga.com/api/v2.1/quotes?token={BENZINGA_API_KEY}&tickers={','.join(tickers)}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "application/json" in response.headers.get("Content-Type", ""):
            return response.json().get("quotes", [])
        else:
            print("Quotes raw response:", response.text[:200])
    except Exception as e:
        print("Error fetching quotes:", e)
    return []

# -------------------- BENZINGA NEWS --------------------
def fetch_benzinga_news():
    url = f"https://api.benzinga.com/api/v2/news?token={BENZINGA_API_KEY}&limit=10"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "application/json" in response.headers.get("Content-Type", ""):
            return response.json()
        else:
            print("Benzinga news raw response:", response.text[:200])
    except Exception as e:
        print("Error fetching Benzinga news:", e)
    return []

def fetch_news_fallback():
    url = f"https://newsapi.org/v2/everything?q=stock%20market&apiKey={NEWS_API_KEY}&pageSize=10"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "application/json" in response.headers.get("Content-Type", ""):
            return response.json().get("articles", [])
        else:
            print("NewsAPI raw response:", response.text[:200])
    except Exception as e:
        print("Error fetching NewsAPI:", e)
    return []

# -------------------- FILTER ENGINE --------------------
def filter_quotes(quotes, change_thresh, price_min, price_max):
    filtered = []
    for q in quotes:
        symbol = q.get("symbol")
        price = float(q.get("ask_price", 0))
        change_pct = float(q.get("percent_change", 0))
        volume = q.get("volume", 0)

        if (change_pct >= change_thresh and
            price_min <= price <= price_max):
            filtered.append({
                "Symbol": symbol,
                "Price": price,
                "Change (%)": change_pct,
                "Volume": volume
            })
    return filtered

# -------------------- STREAMLIT UI --------------------
def plot_trend(symbol):
    plt.figure(figsize=(6, 3))
    plt.plot([1, 2, 3, 4, 5], [10, 12, 15, 14, 18], marker="o", color="blue")
    plt.title(f"{symbol} Trend Projection")
    plt.xlabel("Days")
    plt.ylabel("Price")
    st.pyplot(plt)

def main():
    st.set_page_config(page_title="Tadi's Watchlist Scanner", layout="wide")

    # Auto-refresh every 60 seconds
    st_autorefresh(interval=60000, limit=None, key="refresh")

    st.title("📈 Tadi's Watchlist Scanner")
    st.subheader("Real-time Benzinga quotes + news")

    col1, col2, col3 = st.columns([1, 2, 1])

    # Left: Filters
    with col1:
        st.markdown("### 🔧 Adjust Filters")
        change_thresh = st.slider("Daily % Change", 0, 100, 5)
        price_min, price_max = st.slider("Price Range ($)", 1, 500, (1, 200))

    # Middle: Filtered Watchlist
    with col2:
        st.markdown("### 🚀 Watchlist Movers")
        quotes = fetch_quotes(WATCHLIST)
        filtered = filter_quotes(quotes, change_thresh, price_min, price_max)

        if filtered:
            for stock in filtered:
                st.markdown(f"#### {stock['Symbol']} — ${stock['Price']} ({stock['Change (%)']}%)")
                st.write(f"📊 Volume: {stock['Volume']}")
                plot_trend(stock['Symbol'])
                st.markdown("---")
        else:
            st.warning("No watchlist stocks currently meet criteria.")

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



