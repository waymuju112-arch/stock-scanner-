import requests
import streamlit as st
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# --- LOAD ENV OR SECRETS ---
if st.secrets:  # running on Streamlit Cloud
    API_KEY    = st.secrets["ALPHAVANTAGE_KEY"]
    EMAIL_USER = st.secrets["EMAIL_USER"]
    EMAIL_PASS = st.secrets["EMAIL_PASS"]
    EMAIL_TO   = st.secrets["EMAIL_TO"]
else:  # running locally
    load_dotenv()
    API_KEY    = os.getenv("ALPHAVANTAGE_KEY")
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
    EMAIL_TO   = os.getenv("EMAIL_TO")

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

# --- FOREX DATA FUNCTION ---
def get_forex_data(from_symbol, to_symbol):
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={from_symbol}&to_currency={to_symbol}&apikey={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("Realtime Currency Exchange Rate", {})
    return None

# --- STREAMLIT UI ---
st.title("💱 Multi-Pair Forex Scanner with Alerts")

# Add a manual refresh button
if st.button("🔄 Refresh now"):
    st.experimental_rerun()

pairs = ["USD/ZAR", "EUR/USD", "GBP/JPY", "USD/JPY"]  # core watchlist
thresholds = {
    "USD/ZAR": 18.00,
    "EUR/USD": 1.10,
    "GBP/JPY": 185.00,
    "USD/JPY": 150.00
}

results = []
for pair in pairs:
    base, quote = pair.split("/")
    fx_data = get_forex_data(base, quote)
    if fx_data:
        rate = float(fx_data.get("5. Exchange Rate", 0))
        results.append({"Pair": pair, "Rate": rate})

        # Display metric
        st.metric(label=f"{pair} Exchange Rate", value=rate)

        # Alert if above threshold
        if rate > thresholds[pair]:
            alert_body = f"{pair} is trading at {rate}, above threshold {thresholds[pair]}"
            send_email_alert(f"Forex Alert: {pair}", alert_body, EMAIL_TO)
            st.success(f"📧 Email alert sent for {pair}!")
    else:
        st.warning(f"No data for {pair}")

# Show summary table
if results:
    st.subheader("Scanner Results")
    st.dataframe(results)









