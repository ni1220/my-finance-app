import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_datareader.data as web
import sqlite3
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- [1. 資料抓取防護模組：使用快取減少被封鎖機率] ---

@st.cache_data(ttl=3600)  # 快取 1 小時，避免頻繁請求 Yahoo
def get_stock_data_cached(ticker_code):
    """安全抓取股票基本資料與歷史價格"""
    t = yf.Ticker(ticker_code)
    # 這裡分開抓取，避免其中一個失敗導致全部報錯
    info = t.info
    hist = t.history(period="1y")
    return info, hist

@st.cache_data(ttl=900)  # 新聞快取 15 分鐘
def get_news_cached(ticker_code):
    """抓取最新新聞清單"""
    return yf.Ticker(ticker_code).news

@st.cache_data(ttl=86400)  # 宏觀指標快取 24 小時
def get_fred_data_cached(fred_id):
    """從 FRED 抓取經濟元數據"""
    start = datetime.now() - timedelta(days=730)
    return web.DataReader(fred_id, 'fred', start)

# --- [2. 資料庫功能模組] ---

def init_db():
    conn = sqlite3.connect('finance_pro_v3.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sentiment_logs 
                 (date TEXT, ticker TEXT, price REAL, sentiment REAL)''')
    conn.commit()
    conn.close()

def save_to_db(ticker, price, sentiment):
    conn = sqlite3.connect('finance_pro_v3.db')
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO sentiment_logs VALUES (?, ?, ?, ?)", (now, ticker, price, sentiment))
    conn.commit()
    conn.close()

init_db()

# --- [3. 工具初始化] ---
analyzer = SentimentIntensityAnalyzer()
translator = GoogleTranslator(source='auto', target='zh-TW')

def safe_translate(text):
    if not text or text == "無資料": return text
    try: return translator.translate(text[:1000]) 
    except: return text

# --- [4. 頁面介面設定] ---
st.set_page_config(page_title="金融戰情終端 Pro v3.5", layout="wide")
st.title("🛡️ 專業金融整合分析系統 (穩定快取版)")

# --- [5. 側邊欄：完整功能區] ---
st.sidebar.header("🔍 核心標的選擇")

# 完整熱門名單：確保 Key 與 radio 完全對應
popular_stocks = {
    "美股": {
        "輝達 (NVDA)": "NVDA", "蘋果 (AAPL)": "AAPL", "特斯拉 (TSLA)": "TSLA",
        "微軟 (MSFT)": "MSFT", "亞馬遜 (AMZN)": "AMZN", "Google (GOOGL)": "GOOGL",
        "Meta (META)": "META", "超微 (AMD)": "AMD", "Netflix (NFLX)": "NFLX", "台積電 ADR (TSM)": "TSM"
    },
    "台股": {
        "台積電 (2330.TW)": "2330.TW", "鴻海 (2317.TW)": "2317.TW", "聯發科 (2454.TW)": "2454.TW",
        "富邦金 (2881.TW)": "2881.TW", "國泰金 (2882.TW)": "2882.TW", "台達電 (2308.TW)": "2308.TW",
        "廣達 (2382.TW)": "2382.TW", "長榮 (2603.TW)": "2603.TW", "台塑 (1301.TW)": "1301.TW", "中華電 (2412.TW)": "2412.TW"
    }
}

market_choice = st.sidebar.radio("選擇市場分類", ["美股", "台股", "自定義輸入"])

if market_choice == "自定義輸入":
    target_stock = st.sidebar.text_input("輸入代碼 (例: TSLA 或 2330.TW)", "AAPL").upper()
else:
    selected_name = st.sidebar.selectbox("熱門標的快選", list(popular_stocks[market_choice].keys()))
    target_stock = popular_stocks[market_choice][selected_name]

# 宏觀指標擴充
st.sidebar.markdown("---")
st.sidebar.subheader("📈 宏觀數據控制")
common_fred = {
    "10年期美債利率": "DGS10",
    "核心 CPI (通膨)": "CPILFESL",
    "聯邦基金利率": "FEDFUNDS",
    "失業率": "UNRATE",
    "GDP 季度成長率": "A191RL1Q225SBEA",
    "黃金價格": "GOLDAMGBD228NLBM",
    "M2 貨幣供給量": "M2SL"
}
fred_mode = st.sidebar.selectbox("常用經濟指標", list(common_fred.keys()))
custom_fred_id = st.sidebar.text_input("自定義 FRED ID", common_fred[fred_mode])

# --- [6. 主要功能分頁] ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["💡 產業資訊", "📈 市場指標", "⚠️ 風險與新聞", "🛠️ 專業工具箱", "📜 歷史紀錄庫"])

# --- Tab 1: 產業深度資訊 ---
with tab1:
    try:
        with st.spinner('正在從伺服器安全提取基本面資料...'):
            info, hist = get_stock_data_cached(target_stock)
        
        st.header(f"🏢 {info.get('longName', target_stock)} 深度分析")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.metric("目前價格", f"${info.get('currentPrice', 'N/A')}")
            st.write(f"**產業:** {info.get('industry', '未知')}")
            st.write(f"**國家/區域:** {info.get('country', '未知')}")
            st.write("**--- 公司業務核心摘要 (中譯) ---**")
            st.write(safe_translate(info.get('longBusinessSummary', 'Yahoo Finance 暫未提供詳細摘要。')))
            
        with col2:
            if not hist.empty:
                fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'],
                                                    increasing_line_color='red', decreasing_line_color='green')])
                fig.update_layout(title=f"{target_stock} 最近一年日K線圖", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("查無此代碼的歷史股價資料。")
    except Exception as e:
        st.error(f"❌ 無法讀取資料。原因：{str(e)}")
        st.info("💡 解決方案：請確認代碼格式 (台股需加 .TW) 或 1 分鐘後重新整理頁面。")

# --- Tab 2: 市場宏觀指標 ---
with tab2:
    st.header("🌍 全球宏觀經濟監測")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader(f"指標趨勢：{fred_mode}")
        try:
            df_macro = get_fred_data_cached(custom_fred_id)
            st.line_chart(df_macro)
            st.caption(f"資料來源：FRED (代碼: {custom_fred_id})")
        except: st.warning("無法載入該 FRED 代碼，請檢查 ID 是否正確。")
    with c2:
        st.subheader("微觀熱力圖 (點到面分析)")
        st.markdown("[👉 開啟 Finviz 全球股市熱力圖](https://finviz.com/map.ashx)")
        st.info("💡 Finviz 熱力圖能幫您快速分辨目前全球資金流向，綠色代表上漲，紅色代表下跌。")

# --- Tab 3: 風險與新聞分析 ---
with tab3:
    st.header("🤖 AI 新聞情緒與原文追蹤")
    news_data = get_news_cached(target_stock)
    if news_data:
        sentiments = []
        display_num = 15 # 固定擴充顯示數量
        with st.spinner('AI 正在解讀並翻譯最新 15 則新聞...'):
            for n in news_data[:display_num]:
                content = n.get('content', n)
                t = content.get('title') or content.get('headline') or "無標題"
                l = content.get('clickThroughUrl') or content.get('url') or "#"
                p = content.get('publisher') or "未知來源"
                
                score = analyzer.polarity_scores(t)['compound']
                sentiments.append({
                    "新聞標題 (中譯)": safe_translate(t),
                    "發布來源": p,
                    "AI 情緒評價": "🟢 看多" if score > 0.05 else ("🔴 看空" if score < -0.05 else "🟡 中立"),
                    "情緒得分": score,
                    "原文連結": l
                })
        
        df_sent = pd.DataFrame(sentiments)
        st.dataframe(
            df_sent,
            column_config={"原文連結": st.column_config.LinkColumn("閱讀原文", display_text="點擊跳轉")},
            use_container_width=True, hide_index=True
        )
        
        avg_score = df_sent['情緒得分'].mean()
        st.metric("市場綜合情緒得分", round(avg_score, 2), delta="情緒偏多" if avg_score > 0 else "情緒偏空")
        
        if st.button("💾 紀錄本次分析數據"):
            try:
                save_to_db(target_stock, info.get('currentPrice', 0), avg_score)
                st.success(f"已成功紀錄 {target_stock} 於資料庫！")
            except: st.error("紀錄失敗，請檢查資料庫狀態。")
    else:
        st.warning("目前 Yahoo Finance 暫無此標的的相關新聞。")

# --- Tab 4: 專業工具箱 (詳細擴充) ---
with tab4:
    st.header("🛠️ 專業金融工具與進階資源")
    st.info("這些工具提供『未公開報告』與『深度分析』，是分析師必備的點到面資源。")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("🔍 產業與市場深度搜尋")
        st.write("**[AlphaSense](https://www.alpha-sense.com/)**")
        st.caption("AI 金融搜尋引擎：掃描數萬份財報、法說會逐字稿 (Transcripts)，自動提取產業趨勢。")
        
        st.write("**[Koyfin](https://www.koyfin.com/)**")
        st.caption("視覺化基本面對比：適合追蹤產業板塊 (Sectors) 的資金流向與估值對比。")
        
        st.write("**[Statista](https://www.statista.com/)**")
        st.caption("全球產業報告：提供未來五年預測、各國市場份額及結構化數據圖表。")

    with col_t2:
        st.subheader("📊 宏觀數據與情緒風險")
        st.write("**[FRED 數據庫](https://fred.stlouisfed.org/)**")
        st.caption("權威宏觀指標：提供全球通膨、利率、GDP 等超過 80 萬種數據元數據。")
        
        st.write("**[Fear & Greed Index](https://edition.cnn.com/markets/fear-and-greed)**")
        st.caption("量化情緒指標：整合股價動能、垃圾債券需求等多項指標計算市場恐懼程度。")
        
        st.write("**[Financial Juice](https://www.financialjuice.com/)**")
        st.caption("即時語音新聞：第一時間捕捉引發市場大幅波動的黑天鵝事件。")

# --- Tab 5: 歷史紀錄庫 ---
with tab5:
    st.header("📜 歷史分析紀錄與聯動對比")
    conn = sqlite3.connect('finance_pro_v3.db')
    df_db = pd.read_sql_query(f"SELECT * FROM sentiment_logs WHERE ticker='{target_stock}'", conn)
    conn.close()
    
    if not df_db.empty:
        # 
        fig_corr = go.Figure()
        fig_corr.add_trace(go.Scatter(x=df_db['date'], y=df_db['price'], name="股價 (Price)", yaxis="y1"))
        fig_corr.add_trace(go.Scatter(x=df_db['date'], y=df_db['sentiment'], name="AI 情緒分數", yaxis="y2", mode='lines+markers'))
        
        fig_corr.update_layout(
            title=f"{target_stock} 歷史情緒 vs 股價 關聯性分析",
            yaxis=dict(title="價格 (Price)"),
            yaxis2=dict(title="情緒得分 (Sentiment)", overlaying="y", side="right"),
            legend=dict(x=0, y=1.1, orientation="h")
        )
        st.plotly_chart(fig_corr, use_container_width=True)
        st.write("--- 歷史數據列表 ---")
        st.dataframe(df_db, use_container_width=True)
    else:
        st.info("目前尚未有您的手動紀錄。請在『風險與新聞』分頁點擊儲存按鈕，積累屬於您的大數據。")

st.sidebar.markdown("---")
st.sidebar.write("✅ 系統版本：3.5 (穩定發布版)")
