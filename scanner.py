# scanner.py

import time
import yfinance as yf
from yfinance.exceptions import YFRateLimitError
import requests
import streamlit as st
import matplotlib.pyplot as plt
import smtplib
from email.mime.text import MIMEText

# -------------------- CONFIG --------------------
NEWS_API_KEY = 'YOUR_NEWSAPI_KEY'   # get one free at https://newsapi.org
EMAIL_ADDRESS = 'your_email@gmail.com'
EMAIL_PASSWORD = 'YOUR_APP_PASSWORD'
RECIPIENT_EMAIL = 'recipient_email@gmail.com'
TICKERS = ['WKEY', 'IPHA', 'LQDP', 'CGTL', 'ONDS', 'VMAR', 'CKPT', 'UBXG', 'DRUG']

# -------------------- SAFE HISTORY WRAPPER --------------------
def safe_history(symbol, period="7d", retries=3, delay=5):
    """Fetch stock history with retry logic to handle YFRateLimitError."""
    for attempt in range(retries):
        try:
            return yf.Ticker(symbol).history(period=period)
        except YFRateLimitError:
            if attempt < retries - 1:
                time.sleep(delay)  # wait before retry
            else:
                return None

# -------------------- SCANNER LOGIC --------------------
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
        info = yf.Ticker(symbol).info
        float_shares = info.get('floatShares', 0) / 1e6

        results.append({
            'Symbol': symbol,
            'Price': round(price, 2),
            'Change (%)': round(price_change, 2),
            'Volume Ratio': round(volume_ratio, 2),
            'Float (M)': round(float_shares, 2),
            'History': hist
        })
    return results

# -------------------- NEWS FETCH VIA REQUESTS --------------------
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

# -------------------- EMAIL DELIVERY --------------------
def send_email(filtered_stocks):
    body = "Tadi's Scanner Results:\n\n"
    for stock in filtered_stocks:
        body += f"{stock['Symbol']} | Price: ${stock['Price']} | Change: {stock['Change (%)']}% | Vol Ratio: {stock['Volume Ratio']} | Float: {stock['Float (M)']}M\n"
        for headline in stock['News']:
            body += f"  - {headline}\n"
        body += "\n"

    msg = MIMEText(body)
    msg['Subject'] = 'Tadi’s Daily Scanner Results'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECIPIENT_EMAIL

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

# -------------------- STREAMLIT UI --------------------
def plot_trend(history, symbol):
    plt.figure(figsize=(6, 3))
    plt.plot(history.index, history['Close'], marker='o', linestyle='-', color='green')
    plt.title(f'{symbol} Price Trend')
    plt.xlabel('Date')
    plt.ylabel('Close Price')
    st.pyplot(plt)

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

    st.title("📈 Tadi's Scanner — Market Momentum Dashboard")
    st.subheader("Identifying High Demand, Low Supply Stocks")

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
        send_email(filtered)
        st.success("Email sent with scanner results!")
    else:
        st.warning("No stocks met all criteria today.")

if __name__ == "__main__":
    main()





