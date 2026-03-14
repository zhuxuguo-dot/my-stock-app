import streamlit as st
import akshare as ak
import pandas as pd
from openai import OpenAI
import base64
from io import BytesIO
from PIL import Image

# --- 1. 页面配置 ---
st.set_page_config(page_title="Kimi 驱动-股票形态搜寻器", layout="wide")
st.title("📈 Kimi AI 股票形态搜寻器")
st.caption("基于 Kimi 大模型分析 K 线形态，并在全市场寻找相似走势")

# --- 2. 配置 Kimi API ---
api_key = st.sidebar.text_input("请输入你的 Moonshot (Kimi) API Key", type="password")

def encode_image(image):
    """将上传的图片转为 Base64 格式，以便发给 Kimi"""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# --- 3. 核心功能函数 ---
def analyze_with_kimi(image_base64):
    """调用 Kimi 的视觉能力分析图片"""
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.moonshot.cn/v1",
    )
    
    response = client.chat.completions.create(
        model="‌moonshot-v1-8k", # 如果你的账户有视觉权限，请确认模型名
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "分析这张K线图最近20个节点的趋势，仅输出20个代表价格波动的相对数值（如收盘价序列），用逗号分隔，不要有文字说明。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                ],
            }
        ],
    )
    return response.choices[0].message.content

def get_stock_data(code, days=40):
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        return df['收盘'].tail(days).tolist()
    except:
        return None

# --- 4. 界面布局 ---
if not api_key:
    st.warning("请在左侧边栏输入 Moonshot API Key 以启用 AI 功能")
else:
    uploaded_file = st.file_uploader("上传 K 线截图", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="待分析形态", width=400)
        
        if st.button("开始匹配"):
            with st.spinner("Kimi 正在深度解析形态..."):
                try:
                    img_b64 = encode_image(img)
                    trend_str = analyze_with_kimi(img_b64)
                    base_pattern = [float(x.strip()) for x in trend_str.split(',')]
                    
                    st.info(f"AI 提取趋势成功：{base_pattern[:5]}...")
                    
                    # 扫描逻辑
                    results = []
                    pool = ak.stock_zh_a_spot_em() 
                    # 演示：只搜寻前 30 只
                    test_codes = pool['代码'].head(30).tolist()
                    test_names = pool['名称'].head(30).tolist()
                    
                    p_bar = st.progress(0)
                    for i, code in enumerate(test_codes):
                        target_data = get_stock_data(code, days=len(base_pattern))
                        if target_data:
                            # 计算相关系数
                            s1, s2 = pd.Series(base_pattern), pd.Series(target_data)
                            sim = s1.corr(s2)
                            if sim > 0.8:
                                results.append({"代码": code, "名称": test_names[i], "相似度": f"{sim:.2%}"})
                        p_bar.progress((i + 1) / len(test_codes))
                    
                    if results:
                        st.table(pd.DataFrame(results))
                    else:
                        st.warning("暂未发现高度相似股票。")
                except Exception as e:
                    st.error(f"分析出错：{e}")
