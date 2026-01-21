# scanner_secure_rapidapi_alpha_polygon.py

import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import requests
from streamlit_autorefresh import st_autorefresh

# -------------------- CONFIG --------------------
POLYGON_API_KEY = st.secrets["POLYGON_API_KEY"]
ALPHA_API_KEY = st.secrets["ALPHA_API_KEY"]
RAPIDAPI_KEY = st.secrets["RAPIDAPI_KEY"]


# -------------------- POLYGON NEWS --------------------
@st.cache_data(ttl=600)
def fetch_polygon_news():
    url = f"https://api.polygon.io/v2/reference/news?apiKey={POLYGON_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and "application/json" in r.headers.get("Content-Type", ""):
            return r.json().get("results", [])
    except Exception as e:
        st.warning("Polygon news fetch failed.")
    return []

# -------------------- Yahoo Finance via RapidAPI --------------------
@st.cache_data(ttl=300)
def fetch_yahoo_movers(category="gainers", limit=100):
    url = f"https://yahoo-finance15.p.rapidapi.com/api/yahoo/market/{category}"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "yahoo-finance15.p.rapidapi.com"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            df = pd.DataFrame(data.get("quotes", []))
            return df.head(limit)
    except Exception as e:
        st.warning(f"Yahoo {category} fetch failed.")
    return pd.DataFrame()

# -------------------- Alpha Vantage OHLC --------------------
@st.cache_data(ttl=600)
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
        st.warning(f"Alpha Vantage data fetch failed for {symbol}.")
    return pd.DataFrame()

# -------------------- SCORING ENGINE --------------------
def score_stocks(df, symbol_col="symbol", price_col="regularMarketPrice",
                 change_col="regularMarketChangePercent", volume_col="regularMarketVolume"):
    scored = []
    if not df.empty:
        for _, row in df.iterrows():
            symbol = row.get(symbol_col)
            price = row.get(price_col, 0)
            change_pct = row.get(change_col, 0)
            volume = row.get(volume_col, 0)

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
    st_autorefresh(interval=60000, limit=100, key="refresh")

    st.title("📈 Tadi's Market Scanner")
    st.caption("Secured and optimized with caching, secrets, and quota protection")

    tab_movers, tab_charts, tab_news = st.tabs(["📊 Market Movers", "📈 Charts", "📰 News"])

    # Fetch data
    gainers = fetch_yahoo_movers("gainers")
    losers = fetch_yahoo_movers("losers")
    active = fetch_yahoo_movers("mostactive")

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

        st.subheader("🔥 Most Active")
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









