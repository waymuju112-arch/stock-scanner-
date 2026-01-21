# scanner.py

import time
import yfinance as yf
from yfinance.exceptions import YFRateLimitError
import requests
import streamlit as st
import matplotlib.pyplot as plt

# -------------------- CONFIG --------------------
NEWS_API_KEY = 'YOUR_NEWSAPI_KEY'  # Get one free at https://newsapi.org

# ✅ Expanded ticker list (12 symbols)
TICKERS = [
    'AAPL', 'MSFT', 'TSLA', 'NVDA', 'AMD',
    'GOOGL', 'AMZN', 'META', 'NFLX', 'BAC',
    'JPM', 'XOM'
]

# -------------------- SAFE HISTORY WRAPPER --------------------
def safe_history(symbol, period="7d", retries=3, delay=5):
    for attempt in range(retries):
        try:
            return yf.Ticker(symbol).history(period=period)
        except YFRateLimitError:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                return None

# -------------------- SCANNER LOGIC --------------------
@st.cache_data(ttl=300)
def scan_stocks(tickers):
    results = []
    for symbol in tickers:
        hist = safe_history(symbol)
        if hist is None or len(hist) < 2:
            continue

        today = hist.iloc[-1]
        yesterday = hist.iloc[-2]
        price_change = ((today['Close'] - yesterday['Close']) / yesterday['Close']) * 100
        volume_ratio = today['Volume'] / hist['Volume'].mean()
        price = today['Close']

        ticker_obj = yf.Ticker(symbol)
        try:
            float_shares = ticker_obj.fast_info.get('sharesOutstanding', 0) / 1e6
        except Exception:
            float_shares = 0

        results.append({
            'Symbol': symbol,
            'Price': round(price, 2),
            'Change (%)': round(price_change, 2),
            'Volume Ratio': round(volume_ratio, 2),
            'Float (M)': round(float_shares, 2),
            'History': hist
        })
    return results

# -------------------- NEWS FETCH --------------------
def get_news(symbol):
    url = f"https://newsapi.org/v2/everything?q={symbol}&language=en&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        if "articles" in data:
            return [a['title'] for a in data['articles'][:3]]
    except Exception:
        return []
    return []

# -------------------- CRITERIA FILTER --------------------
def filter_criteria(stock_data):
    filtered = []
    for stock in stock_data:
        if (stock['Volume Ratio'] >= 5 and
            stock['Change (%)'] >= 30 and
            3 <= stock['Price'] <= 20 and
            stock['Float (M)'] <= 5):
            stock['News'] = get_news(stock['Symbol'])
            filtered.append(stock)
    return filtered

# -------------------- STREAMLIT UI --------------------
def plot_trend(history, symbol):
    plt.figure(figsize=(6, 3))
    plt.plot(history.index, history['Close'], marker='o', linestyle='-', color='green')
    plt.title(f'{symbol} Price Trend')
    plt.xlabel('Date')
    plt.ylabel('Close Price')
    st.pyplot(plt)

def show_criteria():
    st.markdown("### 📋 Scanner Criteria")
    st.markdown("""
    **Indicators of High Demand and Low Supply**
    - ✅ Demand: 5x Relative Volume (5x Above Average Volume today)  
    - ✅ Demand: Already up 30% on the day  
    - ✅ Demand: There is a News Event moving the stock higher  
    - ✅ Demand: Price Between $3.00 - $20.00  
    - ✅ Supply: Less than 5 million shares available to trade  
    """)

def main():
    st.set_page_config(page_title="Tadi's Scanner", layout="wide")
    st.markdown(
        """
        <style>
        .stApp {
            background-image: url("https://upload.wikimedia.org/wikipedia/commons/6/6f/Wall_Street_sign_NYC.jpg");
            background-size: cover;
            background-position: center;
            color: white;
        }
        </style>
        """, unsafe_allow_html=True
    )

    st.title("📈 Tadi's Scanner — Real-Time Market Dashboard")
    st.subheader("Live momentum vs. scanner criteria")

    col1, col2 = st.columns([1, 2])
    with col1:
        show_criteria()

    with col2:
        with st.spinner("Scanning market..."):
            scanned = scan_stocks(TICKERS)
            filtered = filter_criteria(scanned)

        if filtered:
            for stock in filtered:
                st.markdown(f"### {stock['Symbol']} — ${stock['Price']} ({stock['Change (%)']}%)")
                st.write(f"📊 Volume Ratio: {stock['Volume Ratio']} | 🧮 Float: {stock['Float (M)']}M")
                st.write("📰 News Headlines:")
                for headline in stock['News']:
                    st.write(f"- {headline}")
                plot_trend(stock['History'], stock['Symbol'])
                st.markdown("---")
        else:
            st.warning("No stocks met all criteria right now.")

if __name__ == "__main__":
    main()







