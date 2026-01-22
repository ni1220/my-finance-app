import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_datareader.data as web
import sqlite3
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta
import plotly.graph_objects as go


# --- [資料庫功能模組] ---
def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect('finance_history_v3.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sentiment_history 
                 (date TEXT, ticker TEXT, price REAL, sentiment REAL)''')
    conn.commit()
    conn.close()


def save_to_db(ticker, price, sentiment):
    """儲存分析數據"""
    conn = sqlite3.connect('finance_history_v3.db')
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO sentiment_history VALUES (?, ?, ?, ?)", (now, ticker, price, sentiment))
    conn.commit()
    conn.close()


init_db()

# --- [工具初始化] ---
analyzer = SentimentIntensityAnalyzer()
translator = GoogleTranslator(source='auto', target='zh-TW')


def translate_content(text):
    if not text or text == "無資料": return text
    try:
        return translator.translate(text[:1000])
    except:
        return text


# --- [頁面設定] ---
st.set_page_config(page_title="金融終端 Pro v3.0", layout="wide")
st.title("🛡️ 專業金融整合分析系統 (終極擴充版)")

# --- [側邊欄：核心標的與自定義指標] ---
st.sidebar.header("🔍 核心標的選擇")

# 修正後的熱門標的字典 (Key 必須與 radio 選項一致)
popular_stocks = {
    "美股": {
        "輝達 (NVDA)": "NVDA", "蘋果 (AAPL)": "AAPL", "特斯拉 (TSLA)": "TSLA",
        "微軟 (MSFT)": "MSFT", "亞馬遜 (AMZN)": "AMZN", "Google (GOOGL)": "GOOGL",
        "Meta (META)": "META", "超微 (AMD)": "AMD", "Netflix (NFLX)": "NFLX", "台積電 ADR (TSM)": "TSM"
    },
    "台股": {
        "台積電 (2330.TW)": "2330.TW", "鴻海 (2317.TW)": "2317.TW", "聯發科 (2454.TW)": "2454.TW",
        "富邦金 (2881.TW)": "2881.TW", "國泰金 (2882.TW)": "2882.TW", "台達電 (2308.TW)": "2308.TW",
        "廣達 (2382.TW)": "2382.TW", "長榮 (2603.TW)": "2603.TW", "台塑 (1301.TW)": "1301.TW",
        "中華電 (2412.TW)": "2412.TW"
    }
}

market_choice = st.sidebar.radio("市場分類", ["美股", "台股", "自定義"])

if market_choice == "自定義":
    target_stock = st.sidebar.text_input("輸入代碼 (例: TSLA 或 2330.TW)", "AAPL")
else:
    # 這裡的 market_choice 會精確對應到 popular_stocks 的 Key
    selected_name = st.sidebar.selectbox("選擇熱門標的", list(popular_stocks[market_choice].keys()))
    target_stock = popular_stocks[market_choice][selected_name]

st.sidebar.markdown("---")
st.sidebar.subheader("📈 宏觀指標控制")
common_fred = {
    "10年期美債利率": "DGS10",
    "核心 CPI (通膨)": "CPILFESL",
    "聯邦基金利率": "FEDFUNDS",
    "失業率": "UNRATE",
    "GDP 季度成長率": "A191RL1Q225SBEA",
    "黃金價格": "GOLDAMGBD228NLBM"
}
fred_mode = st.sidebar.selectbox("常用指標快選", list(common_fred.keys()))
custom_fred_id = st.sidebar.text_input("手動修改 FRED ID", common_fred[fred_mode])

# --- [主要功能分頁] ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["💡 產業資訊", "📈 市場指標", "⚠️ 風險與新聞", "🛠️ 專業工具箱", "📜 歷史相關性"])

ticker = yf.Ticker(target_stock)

# --- Tab 1: 產業資訊 ---
with tab1:
    try:
        info = ticker.info
        st.header(f"🏢 {info.get('longName', target_stock)} 深度分析")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("目前價格", f"${info.get('currentPrice', 'N/A')}")
            st.write(f"**產業:** {info.get('industry', '未知')}")
            st.write(f"**國家:** {info.get('country', '未知')}")
            st.write("**--- 公司業務摘要 (中譯) ---**")
            with st.spinner('翻譯摘要中...'):
                st.write(translate_content(info.get('longBusinessSummary', '無資料')))
        with col2:
            hist = ticker.history(period="1y")
            fig = go.Figure(data=[
                go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'],
                               increasing_line_color='red', decreasing_line_color='green')])
            fig.update_layout(title="最近一年股價走勢圖", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"查無資料或連線問題：{e}")

# --- Tab 2: 市場指標 ---
with tab2:
    st.header("📊 宏觀經濟與微觀工具")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader(f"指標趨勢：{fred_mode}")
        try:
            df_macro = web.DataReader(custom_fred_id, 'fred', datetime.now() - timedelta(days=730))
            st.line_chart(df_macro)
        except:
            st.warning("無法載入此 FRED 代碼，請檢查 ID。")
    with c2:
        st.subheader("微觀熱力圖 (外部連結)")
        st.markdown("[👉 Finviz 全球股市熱力圖](https://finviz.com/map.ashx)")
        st.info("💡 熱力圖能幫您快速分辨目前市場資金流向哪些板塊。")

# --- Tab 3: 風險與新聞 (恢復數量與連結) ---
with tab3:
    st.header("🤖 AI 新聞情緒與風險分析")
    news = ticker.news
    if news:
        sentiments = []
        display_num = 12
        with st.spinner('抓取並翻譯最新新聞中...'):
            for n in news[:display_num]:
                # 相容多種新聞格式
                content = n.get('content', n)
                t = content.get('title') or content.get('headline') or "無標題"
                l = content.get('clickThroughUrl') or content.get('url') or "#"
                p = content.get('publisher') or "未知來源"

                score = analyzer.polarity_scores(t)['compound']
                sentiments.append({
                    "新聞標題 (中譯)": translate_content(t),
                    "來源": p,
                    "情緒評價": "🟢 看多" if score > 0.05 else ("🔴 看空" if score < -0.05 else "🟡 中立"),
                    "得分": score,
                    "原文連結": l
                })

        df_sent = pd.DataFrame(sentiments)
        st.dataframe(
            df_sent,
            column_config={"原文連結": st.column_config.LinkColumn("閱讀原文", display_text="點擊開啟")},
            use_container_width=True, hide_index=True
        )

        avg_score = df_sent['得分'].mean()
        st.metric("綜合情緒分數 (平均)", round(avg_score, 2), delta="偏多" if avg_score > 0 else "偏空")

        if st.button("💾 將本次數據存入資料庫"):
            save_to_db(target_stock, info.get('currentPrice', 0), avg_score)
            st.success(f"已記錄 {target_stock} 於資料庫！")
    else:
        st.warning("暫無相關新聞。")

# --- Tab 4: 工具箱 (詳細介紹) ---
with tab4:
    st.header("🛠️ 專業分析師工具箱 (點到面資源)")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("🔍 產業分析工具")
        st.write("**[AlphaSense](https://www.alpha-sense.com/)**")
        st.caption("AI 金融搜尋引擎，專門掃描數萬份財報與法說會逐字稿，提取專家觀點。")
        st.write("**[Koyfin](https://www.koyfin.com/)**")
        st.caption("提供專業級的視覺化對比，適合進行板塊（Sector）間的資金流向分析。")
        st.write("**[Statista](https://www.statista.com/)**")
        st.caption("全球最大的市場研究數據庫，提供產業趨勢預測與結構化圖表。")
    with col_t2:
        st.subheader("📊 宏觀與風險工具")
        st.write("**[CNN Fear & Greed](https://edition.cnn.com/markets/fear-and-greed)**")
        st.caption("量化市場心理的指標，包含股價動能、避險需求等多維度數據。")
        st.write("**[FRED](https://fred.stlouisfed.org/)**")
        st.caption("由聖路易斯聯準會提供，是獲取全球經濟『元數據』的最權威免費來源。")

# --- Tab 5: 歷史相關性 ---
with tab5:
    st.header("📜 歷史紀錄與趨勢對比")
    conn = sqlite3.connect('finance_history_v3.db')
    df_db = pd.read_sql_query(f"SELECT * FROM sentiment_history WHERE ticker='{target_stock}'", conn)
    conn.close()

    if not df_db.empty:
        fig_corr = go.Figure()
        fig_corr.add_trace(go.Scatter(x=df_db['date'], y=df_db['price'], name="股價", yaxis="y1"))
        fig_corr.add_trace(
            go.Scatter(x=df_db['date'], y=df_db['sentiment'], name="情緒得分", yaxis="y2", mode='lines+markers'))

        fig_corr.update_layout(
            title=f"{target_stock} 歷史聯動分析 (情緒 vs 股價)",
            yaxis=dict(title="價格"),
            yaxis2=dict(title="情緒得分", overlaying="y", side="right"),
            legend=dict(x=0, y=1.1, orientation="h")
        )
        st.plotly_chart(fig_corr, use_container_width=True)
        st.dataframe(df_db, use_container_width=True)
    else:
        st.info("尚未有存檔紀錄，請至『風險與新聞』分頁進行存檔。")

st.sidebar.markdown("---")
st.sidebar.write("✅ 系統版本：3.0 (終極擴充版)")