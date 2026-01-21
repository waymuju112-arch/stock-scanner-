# scanner_finnhub_alpha_polygon_news.py

import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh

# -------------------- CONFIG --------------------
POLYGON_API_KEY = "aZTfdpYgZ0kIAVwdILxPygSHdZ0CrDBu"
ALPHA_API_KEY = "HV1L0BLBFPRE2FYQ"
FINNHUB_API_KEY = "d5o3171r01qma2b78u4gd5o3171r01qma2b78u50"

# -------------------- POLYGON NEWS --------------------
def fetch_polygon_news():
    url = f"https://api.polygon.io/v2/reference/news?apiKey={POLYGON_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and "application/json" in r.headers.get("Content-Type", ""):
            return r.json().get("results", [])
    except Exception as e:
        print("Error fetching Polygon news:", e)
    return []

# -------------------- FINNHUB MOVERS --------------------
def fetch_finnhub_movers():
    url = f"https://finnhub.io/api/v1/stock/market-movers?token={FINNHUB_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            gainers = pd.DataFrame(data.get("gainers", []))
            losers = pd.DataFrame(data.get("losers", []))
            active = pd.DataFrame(data.get("mostActive", []))
            return gainers, losers, active
    except Exception as e:
        print("Error fetching Finnhub movers:", e)
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# -------------------- ALPHA VANTAGE OHLC --------------------
def fetch_alpha_daily(symbol):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={ALPHA_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json().get("Time Series (Daily)", {})
            if data:
                df = pd.DataFrame.from_dict(data, orient="index").astype(float)
                df.index = pd.to_datetime(df.index)
                return df.sort_index()
    except Exception as e:
        print(f"Error fetching Alpha Vantage data for {symbol}:", e)
    return pd.DataFrame()

# -------------------- SCORING ENGINE --------------------
def score_stocks(df):
    scored = []
    if not df.empty:
        for _, row in df.iterrows():
            symbol = row.get("symbol")
            price = row.get("price", 0)
            change_pct = row.get("change", 0)
            volume = row.get("volume", 0)

            score_change = min(abs(change_pct) / 10, 1)
            score_volume = min(volume / 1_000_000, 1)
            match_score = round((score_change*0.6 + score_volume*0.4) * 100, 2)

            scored.append({
                "Symbol": symbol,
                "Price": price,
                "Change (%)": change_pct,
                "Volume": volume,
                "Match %": match_score
            })
    return scored

# -------------------- STREAMLIT UI --------------------
def main():
    st.set_page_config(page_title="Tadi's Market Scanner", layout="wide")
    st_autorefresh(interval=60000, limit=None, key="refresh")

    st.title("📈 Tadi's Market Scanner")
    st.caption("Powered by Finnhub (movers) + Alpha Vantage (OHLC charts) + Polygon.io (news)")

    tab_movers, tab_charts, tab_news = st.tabs(["📊 Market Movers", "📈 Charts", "📰 News"])

    # Fetch data
    gainers, losers, active = fetch_finnhub_movers()
    scored_gainers = score_stocks(gainers)
    scored_losers = score_stocks(losers)

    # Market Movers Tab
    with tab_movers:
        st.header("Top Market Movers")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🚀 Gainers")
            if scored_gainers:
                df_gainers = pd.DataFrame(scored_gainers)
                st.dataframe(df_gainers, use_container_width=True)
                st.bar_chart(df_gainers.set_index("Symbol")["Match %"].head(10))
            else:
                st.info("No gainers data available right now.")

        with col2:
            st.subheader("📉 Losers")
            if scored_losers:
                df_losers = pd.DataFrame(scored_losers)
                st.dataframe(df_losers, use_container_width=True)
                st.bar_chart(df_losers.set_index("Symbol")["Match %"].head(10))
            else:
                st.info("No losers data available right now.")

        st.subheader("🔥 Most Active Stocks")
        if not active.empty:
            st.dataframe(active, use_container_width=True)
        else:
            st.info("No active stocks data available right now.")

    # Charts Tab
    with tab_charts:
        st.header("Visual Analytics: Growth vs Decline")
        if scored_gainers or scored_losers:
            labels = ["Gainers", "Losers"]
            sizes = [len(scored_gainers), len(scored_losers)]
            colors = ["green", "red"]

            fig1, ax1 = plt.subplots()
            ax1.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
            ax1.axis("equal")
            st.pyplot(fig1)

            gainers_df = pd.DataFrame(scored_gainers)
            losers_df = pd.DataFrame(scored_losers)
            if not gainers_df.empty and not losers_df.empty:
                avg_gain = gainers_df["Change (%)"].mean()
                avg_loss = losers_df["Change (%)"].mean()
                fig2, ax2 = plt.subplots()
                ax2.plot(["Gainers", "Losers"], [avg_gain, avg_loss], marker="o", color="blue")
                ax2.set_title("Average % Change Comparison")
                ax2.set_ylabel("% Change")
                st.pyplot(fig2)

            # Example OHLC chart for top gainer
            if not gainers_df.empty:
                top_symbol = gainers_df.iloc[0]["Symbol"]
                st.subheader(f"📈 OHLC Chart for {top_symbol}")
                ohlc = fetch_alpha_daily(top_symbol)
                if not ohlc.empty:
                    st.line_chart(ohlc["4. close"])
                else:
                    st.info(f"No OHLC data available for {top_symbol}.")
        else:
            st.info("No chart data available right now.")

    # News Tab
    with tab_news:
        st.header("Latest Market News")
        news = fetch_polygon_news()
        if news:
            for article in news[:10]:
                with st.expander(article.get("title", "News Item")):
                    image_url = article.get("image_url")
                    if image_url:
                        st.image(image_url, width=200)
                    st.write(article.get("description", ""))
                    url = article.get("article_url")
                    if url:
                        st.markdown(f"[Read more]({url})")
        else:
            st.info("No news available right now.")

if __name__ == "__main__":
    main()





