import streamlit as st
import akshare as ak
import pandas as pd
import numpy as np
from scipy.spatial.distance import euclidean
from fastdtw import fastdtw # 需要在requirements添加fastdtw

# --- 1. 页面配置 ---
st.set_page_config(page_title="股票形态自动匹配工具", layout="wide")
st.title("📊 股票形态自动搜索器")
st.info("无需 AI Key：输入一个‘基准走势’，全自动匹配 A 股相似个股。")

# --- 2. 核心功能函数 ---
@st.cache_data(ttl=3600)
def get_stock_data(code, start_date="20240101", end_date="20260314"):
    """获取股票历史数据"""
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        return df
    except:
        return None

def normalize(data):
    """归一化数据，方便不同价格的股票进行对比"""
    return (data - np.min(data)) / (np.max(data) - np.min(data))

# --- 3. 界面逻辑 ---
col1, col2 = st.columns(2)
with col1:
    base_code = st.text_input("1. 输入基准股票代码", value="600519")
with col2:
    days_to_match = st.slider("2. 匹配最近多少天的走势？", 10, 60, 20)

if st.button("开始全市场相似形态搜索"):
    # 获取基准股票最近的形态
    base_df = get_stock_data(base_code)
    if base_df is not None:
        base_series = base_df['收盘'].tail(days_to_match).values
        base_norm = normalize(base_series)
        
        st.write(f"### 基准形态 ({base_code} 最近 {days_to_match} 天)")
        st.line_chart(base_norm)
        
        # 扫描股票池 (为保证速度，演示搜索前 100 只)
        results = []
        with st.spinner("正在对比全市场形态..."):
            pool = ak.stock_zh_a_spot_em()
            codes = pool['代码'].head(100).tolist()
            names = pool['名称'].head(100).tolist()
            
            p_bar = st.progress(0)
            for i, code in enumerate(codes):
                target_df = get_stock_data(code)
                if target_df is not None and len(target_df) >= days_to_match:
                    target_series = target_df['收盘'].tail(days_to_match).values
                    target_norm = normalize(target_series)
                    
                    # 计算相关系数 (相似度)
                    similarity = np.corrcoef(base_norm, target_norm)[0, 1]
                    
                    if similarity > 0.85: # 相似度大于 85%
                        results.append({"代码": code, "名称": names[i], "相似度": f"{similarity:.2%}"})
                p_bar.progress((i + 1) / len(codes))
        
        if results:
            st.write("### 找到以下高度相似股票：")
            # 按相似度排序
            res_df = pd.DataFrame(results).sort_values(by="相似度", ascending=False)
            st.table(res_df)
        else:
            st.warning("全市场暂未发现高度相似形态。")
