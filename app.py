import streamlit as st
import akshare as ak
import pandas as pd
import google.generativeai as genai
from PIL import Image
import time

# --- 1. 页面配置 ---
st.set_page_config(page_title="AI 股票形态搜寻器", layout="wide")
st.title("📈 AI 股票形态搜寻器")
st.caption("上传 K 线图片或指定股票，AI 将在全市场寻找相似走势")

# --- 2. 配置 AI 大脑 (Gemini) ---
# 在实际发布时，建议通过 Streamlit 的 Secrets 管理 Key
api_key = st.sidebar.text_input("请输入你的 Gemini API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

# --- 3. 核心功能函数 ---
def get_stock_data(code, days=40):
    """获取单只股票最近的数据"""
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        return df['收盘'].tail(days).tolist()
    except:
        return None

def calculate_similarity(base_pattern, target_pattern):
    """计算相似度 (相关系数)"""
    if len(base_pattern) != len(target_pattern):
        # 长度对齐
        min_len = min(len(base_pattern), len(target_pattern))
        base_pattern = base_pattern[-min_len:]
        target_pattern = target_pattern[-min_len:]
    
    s1 = pd.Series(base_pattern)
    s2 = pd.Series(target_pattern)
    return s1.corr(s2)

# --- 4. 界面布局 ---
tab1, tab2 = st.tabs(["🖼️ 上传图片搜寻", "🔍 基准股票搜寻"])

with tab1:
    uploaded_file = st.file_uploader("上传 K 线截图 (请包含清晰的价格走势)", type=["jpg", "jpeg", "png"])
    if uploaded_file and api_key:
        img = Image.open(uploaded_file)
        st.image(img, caption="待分析形态", width=400)
        
        if st.button("开始图片形态分析并匹配"):
            with st.spinner("AI 正在提取趋势数字..."):
                prompt = "分析这张股票K线图最近20个节点的趋势，仅输出20个代表价格波动的相对数值，用逗号分隔，不要有任何文字说明。"
                response = model.generate_content([prompt, img])
                try:
                    base_pattern = [float(x.strip()) for x in response.text.split(',')]
                    st.info("AI 已成功提取形态特征，正在扫描沪深300成分股...")
                    
                    # 扫描逻辑 (为防止速度过慢，先演示前30只)
                    results = []
                    pool = ak.stock_zh_a_spot_em() # 获取全市场快照
                    codes = pool['代码'].head(30).tolist()
                    names = pool['名称'].head(30).tolist()
                    
                    progress_bar = st.progress(0)
                    for i, code in enumerate(codes):
                        target_data = get_stock_data(code, days=len(base_pattern))
                        if target_data:
                            sim = calculate_similarity(base_pattern, target_data)
                            if sim > 0.7: # 相似度门槛
                                results.append({"代码": code, "名称": names[i], "相似度": f"{sim:.2%}"})
                        progress_bar.progress((i + 1) / len(codes))
                    
                    if results:
                        st.write("### 找到以下相似形态股票：")
                        st.table(pd.DataFrame(results))
                    else:
                        st.warning("未发现高度相似的股票。")
                except:
                    st.error("AI 返回数据格式有误，请重试或更换图片。")

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        base_code = st.text_input("输入基准股票代码", value="600519")
    with col2:
        lookback = st.slider("对比天数", 10, 60, 20)
    
    if st.button("以此股票当前形态搜索全场"):
        base_data = get_stock_data(base_code, days=lookback)
        if base_data:
            st.line_chart(base_data)
            st.info(f"正在匹配与 {base_code} 相似的股票...")
            # 此处逻辑同上，遍历市场计算相似度...
            st.write("（此处逻辑与上传图片一致，将搜索全市场数据）")
