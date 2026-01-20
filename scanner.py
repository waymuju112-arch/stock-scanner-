import yfinance as yf
import pandas as pd
import streamlit as st
import requests
import smtplib
from email.mime.text import MIMEText

# --- CONFIG ---
NEWS_API_KEY = "acdf78e97d894e5188249f0ca701a3b9"  
EMAIL_USER = "waymuju112@gmail.com"
EMAIL_PASS = "@Waymuju112#2004"  
EMAIL_TO = "recipient_email@gmail.com"

KEYWORDS = ["FDA", "earnings", "upgrade", "acquisition", "merger", "approval"]

# --- EMAIL ALERT FUNCTION ---
def send_email_alert(subject, body, to_email):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, to_email, msg.as_string())
    except Exception as e:
        st.error(f"Email alert failed: {e}")

# --- NEWS FETCH FUNCTION ---
def fetch_news(ticker):
    url = f"https://newsapi.org/v2/everything?q={ticker}&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        articles = response.json().get("articles", [])
        headlines = [a["title"] for a in articles]
        return headlines
    return []

# --- SCANNER FUNCTION ---
def scan_stock(ticker, min_volume, min_change, min_price, max_price):
    stock = yf.Ticker(ticker.strip())
    try:
        data = stock.history(period="5d", interval="15m")  
    except Exception as e:
        st.warning(f"Could not fetch {ticker}: {e}")
        return None

    if data.empty:
        return None

    open_price = data['Open'].iloc[0]
    close_price = data['Close'].iloc[-1]
    volume = data['Volume'].sum()
    change_pct = ((close_price - open_price) / open_price) * 100

    if min_price <= close_price <= max_price and volume >= min_volume and change_pct >= min_change:
        headlines = fetch_news(ticker)
        matched_news = [h for h in headlines if any(k in h for k in KEYWORDS)]

        # --- EMAIL ALERT ---
        alert_body = (
            f"{ticker} passed criteria:\n"
            f"Change: {round(change_pct, 2)}%\n"
            f"Close: {round(close_price, 2)}\n"
            f"Volume: {volume}\n"
            f"News: {matched_news[:3]}"
        )
        send_email_alert(f"Stock Alert: {ticker}", alert_body, EMAIL_TO)

        return {
            "Ticker": ticker.strip(),
            "Change %": round(change_pct, 2),
            "Close": round(close_price, 2),
            "Volume": volume,
            "News Matches": matched_news
        }
    return None

# --- STREAMLIT UI ---
st.title("📈 Tadis Stock Scanner")

tickers = st.text_input("Enter tickers (comma separated)", "AAPL,TSLA,NVDA,AMZN").split(",")
min_volume = st.number_input("Minimum Volume", value=1000000)
min_change = st.number_input("Minimum % Change", value=5)
max_price = st.number_input("Maximum Price", value=20)
min_price = st.number_input("Minimum Price", value=3)

results = []
for ticker in tickers:
    result = scan_stock(ticker, min_volume, min_change, min_price, max_price)
    if result:
        results.append(result)

tab1, tab2 = st.tabs(["Scanner Results", "Charts"])
if results:
    df = pd.DataFrame([{
        "Ticker": r["Ticker"],
        "Change %": r["Change %"],
        "Close": r["Close"],
        "Volume": r["Volume"],
        "News": "; ".join(r["News Matches"][:3])
    } for r in results])
    with tab1:
        st.success("✅ Stocks meeting criteria")
        st.dataframe(df)
    with tab2:
        for r in results:
            st.subheader(f"{r['Ticker']} Price Chart")
            stock = yf.Ticker(r['Ticker'])
            chart_data = stock.history(period="5d", interval="1h")['Close']
            st.line_chart(chart_data)
else:
    st.info("No stocks matched criteria.")




