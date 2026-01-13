import streamlit as st
import pandas as pd
import re
import os
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# --- 页面配置 ---
st.set_page_config(page_title="作业提交检查系统", layout="wide", page_icon="📚")


# --- 核心逻辑函数 ---
def extract_student_id(filename):
    """从文件名提取9位学号"""
    match = re.search(r'\d{9}', str(filename))
    return match.group() if match else None


def process_roster(df):
    """处理上传的花名册，清洗数据"""
    # 跳过前几行非数据行（根据您提供的文本结构，前4行通常是标题信息）
    # 自动定位“学号”所在的行
    header_row = 0
    for i, row in df.iterrows():
        if row.astype(str).str.contains('学号').any():
            header_row = i
            break

    df.columns = df.iloc[header_row]
    df = df.iloc[header_row + 1:].reset_index(drop=True)

    # 清洗学号和姓名列
    id_col = [c for c in df.columns if '学号' in str(c)][0]
    name_col = [c for c in df.columns if '姓名' in str(c)][0]

    roster = df[[id_col, name_col]].dropna()
    roster[id_col] = roster[id_col].astype(str).str.extract(r'(\d{9})')
    roster = roster.dropna(subset=[id_col])
    return roster.rename(columns={id_col: '学号', name_col: '姓名'})


# --- 侧边栏：文件上传 ---
with st.sidebar:
    st.header("📁 数据导入")
    roster_file = st.file_uploader("上传花名册 (Excel)", type=['xlsx'])

    st.info("""
    **作业文件夹结构说明：**
    由于浏览器安全限制，请在下方手动输入或选择本地作业文件。
    """)
    uploaded_homeworks = st.file_uploader("上传学生作业文件 (可多选)", accept_multiple_files=True)

# --- 主界面 ---
st.title("🎓 Python课程作业提交统计系统")

if roster_file and uploaded_homeworks:
    # 1. 读取花名册
    raw_df = pd.read_excel(roster_file)
    roster_df = process_roster(raw_df)
    all_student_ids = set(roster_df['学号'])
    total_students = len(all_student_ids)

    # 2. 识别已提交学生
    submitted_ids = set()
    for file in uploaded_homeworks:
        sid = extract_student_id(file.name)
        if sid:
            submitted_ids.add(sid)

    # 3. 计算结果
    missing_ids = all_student_ids - submitted_ids
    submit_count = len(submitted_ids)
    missing_count = len(missing_ids)
    submit_rate = submit_count / total_students if total_students > 0 else 0

    # --- 可视化展示 ---
    # 第一排：指标卡
    col1, col2, col3 = st.columns(3)
    col1.metric("应交人数", f"{total_students} 人")
    col2.metric("已交人数", f"{submit_count} 人", delta=f"{submit_count - total_students}")
    col3.metric("提交率", f"{submit_rate:.1%}")

    st.divider()

    # 第二排：图表分析
    c1, c2 = st.columns([1, 1])

    with c1:
        st.subheader("📊 提交比例分布")
        fig_pie = px.pie(
            values=[submit_count, missing_count],
            names=['已交', '未交'],
            color_discrete_sequence=['#2ecc71', '#e74c3c'],
            hole=0.4
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.subheader("📝 未交学生名单")
        missing_df = roster_df[roster_df['学号'].isin(missing_ids)].sort_values('学号')
        st.dataframe(missing_df, use_container_width=True, height=300)

        # 导出Excel功能
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            missing_df.to_excel(writer, index=False)

        st.download_button(
            label="⬇️ 下载未交名单 (Excel)",
            data=output.getvalue(),
            file_name="未交作业名单.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # 第三排：提交详情搜寻
    st.divider()
    st.subheader("🔍 提交详情查询")
    search_query = st.text_input("输入姓名或学号快速查询提交状态")

    roster_df['状态'] = roster_df['学号'].apply(lambda x: "✅ 已交" if x in submitted_ids else "❌ 未交")

    if search_query:
        search_res = roster_df[
            roster_df['姓名'].str.contains(search_query) |
            roster_df['学号'].str.contains(search_query)
            ]
        st.table(search_res)
    else:
        st.write("在上方搜索框输入以查看特定学生状态。")

else:
    # 未上传文件时的欢迎界面
    st.warning("👈 请先在侧边栏上传【花名册】和【学生作业文件】以开始分析。")

    # 展示示例布局
    st.info(
        "系统功能：\n1. 自动解析复杂格式的花名册\n2. 批量匹配作业文件（支持.py等）\n3. 实时生成可视化饼图\n4. 一键导出补交名单")


