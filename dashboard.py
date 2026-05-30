"""
流量分析平台 - Traffic Analytics Platform
主界面 Dashboard
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# 导入分析模块
from traffic_analyzer import TrafficAnalyzer
from behavior_analyzer import BehaviorAnalyzer
from retention_analyzer import RetentionAnalyzer
from anomaly_detector import AnomalyDetector
from forecaster import Forecaster
from segmentation_analyzer import SegmentationAnalyzer

# 页面配置
st.set_page_config(
    page_title="流量分析平台",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 样式
st.markdown("""
<style>
    .main-header {font-size: 2.5rem; font-weight: bold; color: #1f77b4;}
    .metric-card {background-color: #f0f2f6; padding: 20px; border-radius: 10px;}
    .stAlert {border-radius: 10px;}
</style>
""", unsafe_allow_html=True)


def generate_sample_data():
    """生成示例数据"""
    np.random.seed(42)
    n_records = 10000
    
    # 日期范围
    dates = pd.date_range(start='2025-01-01', end='2025-12-31', freq='D')
    
    data = {
        'date': np.random.choice(dates, n_records),
        'user_id': np.random.randint(1, 2000, n_records),
        'session_id': [f'sess_{i}' for i in np.random.randint(1, 5000, n_records)],
        'page': np.random.choice(['home', 'product', 'cart', 'checkout', 'about', 'contact', 'blog'], n_records),
        'source': np.random.choice(['google', 'facebook', 'direct', 'email', 'twitter', 'linkedin'], n_records, 
                                   p=[0.35, 0.25, 0.20, 0.10, 0.05, 0.05]),
        'device': np.random.choice(['desktop', 'mobile', 'tablet'], n_records, p=[0.50, 0.40, 0.10]),
        'country': np.random.choice(['China', 'USA', 'UK', 'Japan', 'Germany', 'France', 'Other'], n_records,
                                    p=[0.30, 0.25, 0.15, 0.10, 0.08, 0.07, 0.05]),
        'duration': np.random.exponential(120, n_records).clip(5, 600),
        'timestamp': pd.date_range(start='2025-01-01', periods=n_records, freq='5min')
    }
    
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date']).dt.date
    return df


def load_data():
    """加载数据"""
    # 检查是否有上传的文件
    if 'uploaded_data' in st.session_state and st.session_state.uploaded_data is not None:
        return pd.read_csv(st.session_state.uploaded_data)
    
    # 检查示例数据文件
    sample_file = 'sample_data.csv'
    if os.path.exists(sample_file):
        return pd.read_csv(sample_file)
    
    # 生成示例数据
    return generate_sample_data()


def main():
    st.markdown('<p class="main-header">流量分析平台</p>', unsafe_allow_html=True)
    st.markdown("专业的网站/APP 流量分析和用户行为洞察平台")
    
    # 侧边栏
    st.sidebar.header("数据管理")
    
    uploaded_file = st.sidebar.file_uploader("上传 CSV 文件", type=['csv'])
    if uploaded_file:
        st.session_state.uploaded_data = uploaded_file
    
    if st.sidebar.button("使用示例数据"):
        if 'uploaded_data' in st.session_state:
            del st.session_state.uploaded_data
    
    # 加载数据
    with st.spinner("正在加载数据..."):
        df = load_data()
    
    st.sidebar.success(f"已加载 {len(df):,} 条记录")
    
    # 主导航
    st.sidebar.header("分析模块")
    module = st.sidebar.radio(
        "选择分析模块",
        ["概览", "流量分析", "行为分析", "留存分析", "异常检测", "预测模型", "细分分析"],
        index=0
    )
    
    # 初始化分析器
    traffic_analyzer = TrafficAnalyzer(df)
    behavior_analyzer = BehaviorAnalyzer(df)
    retention_analyzer = RetentionAnalyzer(df)
    anomaly_detector = AnomalyDetector(df)
    forecaster = Forecaster(df)
    segmentation_analyzer = SegmentationAnalyzer(df)
    
    # 概览模块
    if module == "概览":
        st.header("数据概览")
        
        # 关键指标
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总访问量 (PV)", f"{len(df):,}")
        
        with col2:
            uv = df['user_id'].nunique()
            st.metric("独立访客 (UV)", f"{uv:,}")
        
        with col3:
            sessions = df['session_id'].nunique()
            st.metric("总会话数", f"{sessions:,}")
        
        with col4:
            avg_duration = df['duration'].mean()
            st.metric("平均停留时长", f"{avg_duration:.1f}秒")
        
        # 数据预览
        st.subheader("数据预览")
        st.dataframe(df.head(100), use_container_width=True)
        
        # 数据质量检查
        st.subheader("数据质量")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**缺失值统计:**")
            missing = df.isnull().sum()
            st.write(missing[missing > 0] if any(missing > 0) else "无缺失值")
        
        with col2:
            st.write("**数据类型:**")
            st.write(df.dtypes)
    
    # 流量分析模块
    elif module == "流量分析":
        st.header("流量分析")
        
        # PV/UV 趋势
        st.subheader("PV/UV 趋势")
        daily_stats = df.groupby('date').agg(
            pv=('user_id', 'count'),
            uv=('user_id', 'nunique')
        ).reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily_stats['date'], y=daily_stats['pv'], 
                                name='PV', line=dict(color='#1f77b4', width=2)))
        fig.add_trace(go.Scatter(x=daily_stats['date'], y=daily_stats['uv'], 
                                name='UV', line=dict(color='#ff7f0e', width=2)))
        fig.update_layout(height=400, xaxis_title="日期", yaxis_title="数量",
                         hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
        
        # 流量来源分析
        st.subheader("流量来源分布")
        col1, col2 = st.columns(2)
        
        with col1:
            source_dist = df['source'].value_counts().reset_index()
            source_dist.columns = ['来源', '访问量']
            fig_pie = px.pie(source_dist, values='访问量', names='来源', 
                           color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            source_metrics = df.groupby('source').agg(
                visits=('user_id', 'count'),
                avg_duration=('duration', 'mean')
            ).reset_index()
            fig_bar = px.bar(source_metrics, x='source', y='visits',
                            color='avg_duration', color_continuous_scale='Blues')
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # 设备分布
        st.subheader("设备分布")
        device_dist = df['device'].value_counts().reset_index()
        device_dist.columns = ['设备', '访问量']
        fig_device = px.bar(device_dist, x='设备', y='访问量',
                           color='访问量', color_continuous_scale='Viridis')
        st.plotly_chart(fig_device, use_container_width=True)
        
        # 地域分布
        st.subheader("地域分布")
        country_dist = df['country'].value_counts().head(10).reset_index()
        country_dist.columns = ['国家', '访问量']
        fig_country = px.bar(country_dist, x='国家', y='访问量',
                            color='访问量', color_continuous_scale='Reds')
        st.plotly_chart(fig_country, use_container_width=True)
    
    # 行为分析模块
    elif module == "行为分析":
        st.header("用户行为分析")
        
        # 关键行为指标
        col1, col2, col3 = st.columns(3)
        
        # 跳出率
        session_counts = df.groupby('session_id')['page'].count()
        bounce_rate = (session_counts == 1).sum() / len(session_counts) * 100
        col1.metric("跳出率", f"{bounce_rate:.1f}%")
        
        # 平均访问深度
        avg_depth = session_counts.mean()
        col2.metric("平均访问深度", f"{avg_depth:.2f}页")
        
        # 平均页面停留
        avg_time = df['duration'].mean()
        col3.metric("平均页面停留", f"{avg_time:.1f}秒")
        
        # 页面指标
        st.subheader("页面表现")
        page_metrics = df.groupby('page').agg(
            views=('user_id', 'count'),
            unique_visitors=('user_id', 'nunique'),
            avg_duration=('duration', 'mean')
        ).reset_index().sort_values('views', ascending=False)
        
        fig_pages = px.bar(page_metrics, x='page', y='views',
                          color='avg_duration', color_continuous_scale='Plasma',
                          labels={'page': '页面', 'views': '浏览量', 'avg_duration': '平均停留 (秒)'})
        st.plotly_chart(fig_pages, use_container_width=True)
        
        # 访问深度分布
        st.subheader("访问深度分布")
        depth_dist = session_counts.value_counts().sort_index()
        fig_depth = px.bar(x=depth_dist.index, y=depth_dist.values,
                          labels={'x': '访问页数', 'y': '会话数'})
        st.plotly_chart(fig_depth, use_container_width=True)
        
        # 用户路径分析（桑基图）
        st.subheader("用户行为路径")
        sorted_df = df.sort_values(['session_id', 'timestamp'])
        
        sources, targets, values = [], [], []
        for session_id in sorted_df['session_id'].unique()[:500]:  # 限制数量
            session_data = sorted_df[sorted_df['session_id'] == session_id]
            pages = session_data['page'].tolist()
            for i in range(len(pages) - 1):
                sources.append(pages[i])
                targets.append(pages[i + 1])
                values.append(1)
        
        if sources:
            flow_df = pd.DataFrame({'source': sources, 'target': targets, 'value': values})
            flow_df = flow_df.groupby(['source', 'target']).sum().reset_index()
            
            fig_sankey = go.Figure(data=[go.Sankey(
                node=dict(label=list(set(sources + targets))),
                link=dict(
                    source=[list(set(sources)).index(s) for s in flow_df['source']],
                    target=[list(set(targets)).index(t) for t in flow_df['target']],
                    value=flow_df['value']
                )
            )])
            fig_sankey.update_layout(title_text="用户页面流转", font_size=12, height=500)
            st.plotly_chart(fig_sankey, use_container_width=True)
    
    # 留存分析模块
    elif module == "留存分析":
        st.header("留存分析")
        
        # 创建 Cohort
        retention_analyzer.load_data(df)
        cohort_data = retention_analyzer.create_cohorts(cohort_period='week')
        
        # 留存矩阵
        st.subheader("留存矩阵")
        retention_matrix = retention_analyzer.calculate_retention_matrix()
        
        # 显示留存率
        col1, col2, col3 = st.columns(3)
        rates = retention_analyzer.calculate_retention_rates(retention_matrix)
        
        col1.metric("次日留存", f"{rates.get('day1_retention', 0):.1f}%")
        col2.metric("7 日留存", f"{rates.get('day7_retention', 0):.1f}%")
        col3.metric("30 日留存", f"{rates.get('day30_retention', 0):.1f}%")
        
        # 留存热力图
        fig_retention = px.imshow(retention_matrix, 
                                  labels=dict(x="周期", y="Cohort", color="留存率 (%)"),
                                  color_continuous_scale='RdYlGn')
        fig_retention.update_layout(height=500)
        st.plotly_chart(fig_retention, use_container_width=True)
        
        # 留存曲线
        st.subheader("留存曲线")
        fig_curves = go.Figure()
        for cohort in retention_matrix.index[:10]:  # 显示前 10 个 cohort
            fig_curves.add_trace(go.Scatter(
                x=retention_matrix.columns,
                y=retention_matrix.loc[cohort],
                mode='lines+markers',
                name=str(cohort)[:10]
            ))
        fig_curves.update_layout(xaxis_title="周期", yaxis_title="留存率 (%)",
                                height=400, hovermode='x unified')
        st.plotly_chart(fig_curves, use_container_width=True)
    
    # 异常检测模块
    elif module == "异常检测":
        st.header("异常检测")
        
        # 按日期聚合
        daily_visits = df.groupby('date').size().reset_index(name='visits')
        
        # 统计异常检测
        st.subheader("Z-Score 异常检测")
        anomaly_detector.load_data(daily_visits)
        anomaly_results = anomaly_detector.detect_statistical_anomalies('visits', threshold=2.5)
        
        col1, col2 = st.columns(2)
        col1.metric("检测到异常数", anomaly_results['anomaly_count'])
        col2.metric("异常率", f"{anomaly_results['anomaly_count'] / len(daily_visits) * 100:.1f}%")
        
        # 可视化
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily_visits['date'], y=daily_visits['visits'],
                                name='访问量', line=dict(color='#1f77b4')))
        
        if anomaly_results['anomaly_indices']:
            anomaly_dates = daily_visits.iloc[anomaly_results['anomaly_indices']]['date']
            anomaly_values = daily_visits.iloc[anomaly_results['anomaly_indices']]['visits']
            fig.add_trace(go.Scatter(x=anomaly_dates, y=anomaly_values,
                                    mode='markers', name='异常点',
                                    marker=dict(color='red', size=12)))
        
        fig.add_hline(y=anomaly_results['mean'] + 2.5 * anomaly_results['std'],
                     line_dash="dash", line_color="orange",
                     annotation_text="上阈值")
        fig.add_hline(y=anomaly_results['mean'] - 2.5 * anomaly_results['std'],
                     line_dash="dash", line_color="orange",
                     annotation_text="下阈值")
        fig.update_layout(height=400, xaxis_title="日期", yaxis_title="访问量")
        st.plotly_chart(fig, use_container_width=True)
        
        # 告警列表
        st.subheader("告警列表")
        alerts = anomaly_detector.create_alerts()
        if alerts:
            for alert in alerts[:10]:
                st.warning(f"**{alert['severity'].upper()}** - {alert['message']}")
        else:
            st.success("未检测到异常")
    
    # 预测模型模块
    elif module == "预测模型":
        st.header("流量预测")
        
        # 准备时间序列
        ts = forecaster.prepare_time_series('date', 'user_id')
        
        # 模型选择
        st.subheader("模型拟合")
        model_type = st.selectbox("选择预测模型", ["ARIMA", "指数平滑"])
        
        if model_type == "ARIMA":
            result = forecaster.fit_arima(ts, order=(1, 1, 1))
        else:
            result = forecaster.fit_exponential_smoothing(ts)
        
        if result['status'] == 'success':
            st.success(f"模型拟合成功 - AIC: {result.get('aic', 'N/A'):.2f}")
        else:
            st.error(f"模型拟合失败：{result.get('error', '未知错误')}")
        
        # 预测
        st.subheader("未来预测")
        forecast_days = st.slider("预测天数", 7, 30, 14)
        
        if forecaster.model:
            forecast_result = forecaster.forecast(steps=forecast_days)
            
            # 可视化
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ts.index, y=ts.values,
                                    name='历史数据', line=dict(color='#1f77b4')))
            
            forecast_index = pd.date_range(start=ts.index[-1] + timedelta(days=1), periods=forecast_days)
            fig.add_trace(go.Scatter(x=forecast_index, y=forecast_result['forecast_values'],
                                    name='预测值', line=dict(color='#ff7f0e', dash='dash')))
            fig.add_trace(go.Scatter(x=forecast_index, y=forecast_result['upper_bound'],
                                    name='置信上限', line=dict(color='gray', dash='dot'), showlegend=False))
            fig.add_trace(go.Scatter(x=forecast_index, y=forecast_result['lower_bound'],
                                    name='置信下限', line=dict(color='gray', dash='dot'),
                                    fill='tonexty', showlegend=False))
            
            fig.update_layout(height=400, xaxis_title="日期", yaxis_title="访问量",
                             hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
        
        # 趋势分析
        st.subheader("趋势分析")
        trend_result = forecaster.forecast_trend(ts, steps=30)
        col1, col2 = st.columns(2)
        col1.metric("趋势方向", "上升" if trend_result['trend'] == 'increasing' else "下降")
        col2.metric("R²", f"{trend_result['r_squared']:.3f}")
    
    # 细分分析模块
    elif module == "细分分析":
        st.header("用户细分分析")
        
        # RFM 分析
        st.subheader("RFM 用户价值细分")
        
        # 计算 RFM 指标
        rfm_data = df.groupby('user_id').agg(
            recency=('date', lambda x: (pd.to_datetime('today') - pd.to_datetime(x.max())).days),
            frequency=('session_id', 'nunique'),
            monetary=('duration', 'sum')
        ).reset_index()
        
        segmentation_analyzer.load_data(rfm_data)
        rfm_result = segmentation_analyzer.rfm_segmentation('recency', 'frequency', 'monetary')
        
        # RFM 分布
        col1, col2 = st.columns(2)
        with col1:
            rfm_dist = rfm_result['RFM_segment'].value_counts().reset_index()
            rfm_dist.columns = ['细分群体', '用户数']
            fig_rfm = px.pie(rfm_dist, values='用户数', names='细分群体',
                            color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_rfm, use_container_width=True)
        
        with col2:
            rfm_metrics = rfm_result.groupby('RFM_segment').agg(
                avg_frequency=('frequency', 'mean'),
                avg_monetary=('monetary', 'mean')
            ).reset_index()
            fig_rfm_bar = px.bar(rfm_metrics, x='RFM_segment', y='avg_frequency',
                                color='avg_monetary', color_continuous_scale='Viridis')
            st.plotly_chart(fig_rfm_bar, use_container_width=True)
        
        # K-Means 聚类
        st.subheader("K-Means 用户分群")
        n_clusters = st.slider("分群数量", 3, 10, 5)
        
        feature_cols = ['recency', 'frequency', 'monetary']
        kmeans_result = segmentation_analyzer.create_user_segments(feature_cols, n_clusters)
        
        # 分群特征
        st.write("### 分群特征")
        st.dataframe(kmeans_result['segment_profiles'].round(2), use_container_width=True)
        
        # 分群大小
        col1, col2 = st.columns(2)
        with col1:
            cluster_sizes = pd.DataFrame({
                '分群': list(kmeans_result['cluster_sizes'].keys()),
                '用户数': list(kmeans_result['cluster_sizes'].values())
            })
            fig_cluster = px.bar(cluster_sizes, x='分群', y='用户数',
                                color='用户数', color_continuous_scale='Blues')
            st.plotly_chart(fig_cluster, use_container_width=True)
    
    # 页脚
    st.sidebar.markdown("---")
    st.sidebar.markdown("**流量分析平台 v1.0**")
    st.sidebar.markdown("基于 Streamlit + Plotly 构建")


if __name__ == "__main__":
    main()
