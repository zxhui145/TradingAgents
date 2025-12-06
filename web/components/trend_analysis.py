import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from tradingagents.analysis.trend_analyzer import TrendAnalyzer
import logging

logger = logging.getLogger(__name__)

def render_trend_analysis():
    st.title("📈 趋势分析 & 热门股追踪")
    st.markdown("通过技术指标和成交量分析，发现潜在的趋势反转和起涨点股票。")

    # Initialize Analyzer
    try:
        analyzer = TrendAnalyzer()
    except Exception as e:
        st.error(f"初始化分析器失败: {e}")
        return

    if not analyzer.token:
        st.warning("⚠️ 未检测到 Tushare Token。请在 .env 文件中配置 TUSHARE_TOKEN 以使用此功能。")
        st.info("您可以在 [Tushare大数据社区](https://tushare.pro/) 注册获取 Token。")
        return

    # Sidebar controls for this page
    with st.sidebar:
        st.header("扫描配置")
        scan_limit = st.slider("扫描样本数量", min_value=10, max_value=100, value=30, step=10, help="由于API限制，单次扫描的股票数量")
        min_score = st.slider("最低评分筛选", min_value=0, max_value=100, value=30)
        
        if st.button("🚀 开始扫描", type="primary"):
            st.session_state.scanning = True
            st.session_state.scan_results = None

    # Main area
    if st.session_state.get('scanning', False):
        with st.spinner(f"正在扫描市场 (样本数: {scan_limit})..."):
            try:
                results = analyzer.get_hot_stocks(limit=scan_limit)
                st.session_state.scan_results = results
                st.session_state.scanning = False
            except Exception as e:
                st.error(f"扫描过程中发生错误: {e}")
                st.session_state.scanning = False

    # Display Results
    results = st.session_state.get('scan_results')
    
    if results is not None:
        if len(results) == 0:
            st.info("未找到符合条件的股票。尝试调整筛选条件或重新扫描。")
        else:
            st.success(f"找到 {len(results)} 只潜在热门股票")
            
            # Convert to DataFrame for display
            df_display = pd.DataFrame(results)
            
            # Filter by score
            df_display = df_display[df_display['score'] >= min_score]
            
            if df_display.empty:
                st.warning(f"没有股票达到最低评分 {min_score}")
            else:
                # Display as a list of expanders or a table
                # Let's use a master-detail view layout
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.subheader("股票列表")
                    # Create a selectable table or list
                    # For simplicity, use radio buttons or buttons
                    
                    # Format labels for selection
                    options = [f"{r['ts_code']} - {r['name']} (Score: {r['score']})" for i, r in df_display.iterrows()]
                    selected_option = st.radio("选择查看详情:", options)
                    
                    if selected_option:
                        selected_code = selected_option.split(' - ')[0]
                        selected_stock = next((item for item in results if item["ts_code"] == selected_code), None)
                
                with col2:
                    if selected_stock:
                        st.subheader(f"{selected_stock['name']} ({selected_stock['ts_code']})")
                        
                        # Display Score and Signals
                        score_color = "green" if selected_stock['score'] >= 60 else "orange"
                        st.markdown(f"### 评分: :{score_color}[{selected_stock['score']}]")
                        
                        st.markdown("**触发信号:**")
                        for signal in selected_stock['signals']:
                            st.markdown(f"- ✅ {signal}")
                            
                        st.markdown(f"**行业:** {selected_stock['industry']}")
                        st.markdown(f"**最新收盘:** {selected_stock['latest_close']}")
                        
                        # Fetch and plot detailed chart
                        with st.spinner("加载图表..."):
                            import datetime
                            end_date = datetime.datetime.now().strftime('%Y%m%d')
                            start_date = (datetime.datetime.now() - datetime.timedelta(days=180)).strftime('%Y%m%d')
                            df_chart = analyzer.get_stock_data(selected_stock['ts_code'], start_date, end_date)
                            
                            if df_chart is not None:
                                df_chart = analyzer.calculate_indicators(df_chart)
                                fig = plot_stock_chart(df_chart, selected_stock['name'])
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.error("无法加载图表数据")

def plot_stock_chart(df, name):
    """
    Create a Plotly candlestick chart with MA and Volume.
    """
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=(f'{name} K线图', '成交量'), 
                        row_width=[0.2, 0.7])

    # Candlestick
    fig.add_trace(go.Candlestick(x=df['trade_date'],
                open=df['open'], high=df['high'],
                low=df['low'], close=df['close'], name='K线'), 
                row=1, col=1)

    # Moving Averages
    fig.add_trace(go.Scatter(x=df['trade_date'], y=df['ma5'], line=dict(color='orange', width=1), name='MA5'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['trade_date'], y=df['ma20'], line=dict(color='blue', width=1), name='MA20'), row=1, col=1)

    # Volume
    colors = ['red' if row['open'] < row['close'] else 'green' for i, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df['trade_date'], y=df['vol'], marker_color=colors, name='成交量'), row=2, col=1)

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=600,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig
