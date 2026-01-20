import yfinance as yf
import pandas as pd
import requests
import streamlit as st

# --- CONFIG ---
NEWS_API_KEY = "acdf78e97d894e5188249f0ca701a3b9"  
KEYWORDS = ["FDA", "earnings", "upgrade", "acquisition", "merger", "approval"]
TICKERS = st.text_input("Tickers (comma separated)", "AAPL,TSLA,NVDA,AMZN").split(",")
MIN_VOLUME = st.number_input("Min Volume", value=1000000)
MIN_CHANGE = st.number_input("Min % Change", value=5)
MAX_PRICE = st.number_input("Max Price", value=20)
MIN_PRICE = st.number_input("Min Price", value=3)

# --- FUNCTIONS ---
def fetch_news(ticker):
    url = f"https://newsapi.org/v2/everything?q={ticker}&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        articles = response.json().get("articles", [])
        headlines = [a["title"] for a in articles]
        return headlines
    return []

def scan_stock(ticker):
    stock = yf.Ticker(ticker.strip())
    data = stock.history(period="1d", interval="5m")
    if data.empty:
        return None

    open_price = data['Open'].iloc[0]
    close_price = data['Close'].iloc[-1]
    volume = data['Volume'].sum()
    change_pct = ((close_price - open_price) / open_price) * 100

    if MIN_PRICE <= close_price <= MAX_PRICE and volume >= MIN_VOLUME and change_pct >= MIN_CHANGE:
        headlines = fetch_news(ticker)
        matched_news = [h for h in headlines if any(k in h for k in KEYWORDS)]
        return {
            "Ticker": ticker.strip(),
            "Change %": round(change_pct, 2),
            "Close": round(close_price, 2),
            "Volume": volume,
            "News Matches": matched_news
        }
    return None

# --- SCAN ---
results = []
for ticker in TICKERS:
    result = scan_stock(ticker)
    if result:
        results.append(result)

# --- DISPLAY ---
st.subheader("Scanner Results")
if results:
    df = pd.DataFrame([{
        "Ticker": r["Ticker"],
        "Change %": r["Change %"],
        "Close": r["Close"],
        "Volume": r["Volume"],
        "News": "; ".join(r["News Matches"][:3])  # show top 3 headlines
    } for r in results])
    st.dataframe(df)
else:
    st.info("No stocks matched all criteria.")



