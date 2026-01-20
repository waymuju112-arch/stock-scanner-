import yfinance as yf
import pandas as pd
import streamlit as st

# Title
st.title("📈 Day Trading Scanner Prototype")

# Sidebar filters
tickers = st.text_input("Enter tickers (comma separated)", "AAPL,TSLA,MSFT,NVDA,AMZN").split(",")
min_volume = st.number_input("Minimum Volume", value=5000000)
min_change = st.number_input("Minimum % Change", value=3)
max_price = st.number_input("Maximum Price", value=500)

# Scanner function
def scan_stocks(tickers):
    results = []
    for ticker in tickers:
        stock = yf.Ticker(ticker.strip())
        data = stock.history(period="1d", interval="15m")
        if not data.empty:
            open_price = data['Open'].iloc[0]
            close_price = data['Close'].iloc[-1]
            volume = data['Volume'].sum()
            change_pct = ((close_price - open_price) / open_price) * 100
            
            if change_pct >= min_change and volume >= min_volume and close_price <= max_price:
                results.append({
                    "Ticker": ticker.strip(),
                    "Change %": round(change_pct, 2),
		    "Close": round(close_price, 2),
                    "Volume": volume
                })
    return pd.DataFrame(results)

# Run scanner
scanner_results = scan_stocks(tickers)

# Display results
st.subheader("Scanner Results")
st.dataframe(scanner_results)


