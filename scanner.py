import requests
import streamlit as st
import os
import smtplib
from email.mime.text import MIMEText

# --- CONFIG ---
API_KEY = os.getenv("ALPHAVANTAGE_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO   = os.getenv("EMAIL_TO")

# --- EMAIL ALERT FUNCTION ---
def send_email_alert(subject, body, to_email):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = to_email

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())

# --- FOREX DATA FUNCTION ---
def get_forex_data(from_symbol, to_symbol):
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={from_symbol}&to_currency={to_symbol}&apikey={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["Realtime Currency Exchange Rate"]
    return None

# --- STREAMLIT UI ---
st.title("💱 Forex Scanner with Alerts")

pair = st.text_input("Enter forex pair (e.g., EUR/USD)", "EUR/USD")
base, quote = pair.split("/")

fx_data = get_forex_data(base, quote)

if fx_data:
    rate = float(fx_data["5. Exchange Rate"])
    st.metric(label=f"{base}/{quote} Exchange Rate", value=rate)

    # Example alert: if rate moves above threshold
    threshold = st.number_input("Alert if rate > ", value=1.10)
    if rate > threshold:
        alert_body = f"{base}/{quote} is trading at {rate}, above threshold {threshold}"
        send_email_alert(f"Forex Alert: {base}/{quote}", alert_body, EMAIL_TO)
        st.success("📧 Email alert sent!")
else:
    st.warning("No forex data available.")






