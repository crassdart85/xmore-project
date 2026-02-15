import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
from datetime import datetime, timedelta
import config
import prediction_utils as utils

# Page Config
st.set_page_config(page_title="Xmore2 Dashboard", page_icon="🇪🇬", layout="wide")

# Database Connection
@st.cache_data
def load_data():
    conn = utils.get_db_connection()
    
    # Prices
    prices = pd.read_sql("SELECT * FROM prices", conn)
    prices['date'] = pd.to_datetime(prices['date'])
    
    # Predictions
    preds = pd.read_sql("SELECT * FROM predictions", conn)
    
    # Evaluations
    evals = pd.read_sql("SELECT * FROM evaluations", conn)
    
    conn.close()
    return prices, preds, evals

try:
    prices, preds, evals = load_data()
except Exception as e:
    st.error(f"Error loading database: {e}")
    st.stop()

# Header
st.title("🇪🇬 Xmore2 Trading Dashboard")
st.markdown("**Focus:** Egyptian Exchange (EGX) | **Horizon:** 5 Days")

# Top Stats
col1, col2, col3, col4 = st.columns(4)
col1.metric("Stocks Tracked", len(prices['symbol'].unique()))
col2.metric("Total Predictions", len(preds))
accuracy = 0
if len(evals) > 0:
    accuracy = (evals['was_correct'].sum() / len(evals)) * 100
col3.metric("Overall Accuracy", f"{accuracy:.1f}%")
latest_date = prices['date'].max().strftime('%Y-%m-%d')
col4.metric("Latest Data", latest_date)

# Tabs
tab1, tab2, tab3 = st.tabs(["🚀 Comparison: Future vs History", "📈 Price Charts", "🧐 Detailed Evaluation"])

with tab1:
    st.header("🔮 Future Targets vs 📜 Historical Reality")
    
    col_future, col_history = st.columns(2)
    
    with col_future:
        st.subheader("Future Targets (+5 Days)")
        st.caption(f"Predictions targeting: **{(datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')}**")
        
        # Get active predictions (future target dates)
        future_preds = preds[preds['target_date'] > datetime.now().strftime('%Y-%m-%d')].sort_values('prediction_date', ascending=False).head(10)
        
        if len(future_preds) > 0:
            st.dataframe(future_preds[['symbol', 'agent_name', 'prediction', 'target_date']], use_container_width=True)
        else:
            st.info("No active future predictions found.")

    with col_history:
        lookback_date = utils.get_target_lookback_date(7)
        st.subheader("One Week Ago (Historical)")
        st.caption(f"What happened to predictions targeting: **{lookback_date}**?")
        
        # 1. Find preds targeting this past date
        past_target_preds = preds[preds['target_date'] == lookback_date].copy()
        
        if len(past_target_preds) > 0:
            # 2. Calculate outcomes on the fly
            results = []
            for _, row in past_target_preds.iterrows():
                symbol = row['symbol']
                start_date = row['prediction_date']
                
                # Get prices
                start_row = prices[(prices['symbol'] == symbol) & (prices['date'] == start_date)]
                end_row = prices[(prices['symbol'] == symbol) & (prices['date'] == lookback_date)]
                
                if not start_row.empty and not end_row.empty:
                    s_price = start_row.iloc[0]['close']
                    e_price = end_row.iloc[0]['close']
                    outcome, correct, pct = utils.calculate_outcome(s_price, e_price, row['prediction'])
                    
                    results.append({
                        'Symbol': symbol,
                        'Agent': row['agent_name'],
                        'Pred': row['prediction'],
                        'Actual': outcome,
                        'Change': f"{pct:.2f}%",
                        'Correct': "✅" if correct else "❌"
                    })
            
            if results:
                st.dataframe(pd.DataFrame(results), use_container_width=True)
            else:
                st.warning("Found predictions but missing price data to verify them.")
        else:
            st.info(f"No predictions found that targeted {lookback_date}")

with tab2:
    st.header("Price History & Signals")
    selected_stock = st.selectbox("Select Stock", config.ALL_STOCKS)
    
    stock_data = prices[prices['symbol'] == selected_stock].sort_values('date')
    
    # Base Price Chart
    base = alt.Chart(stock_data).encode(x='date:T')
    
    line = base.mark_line().encode(
        y=alt.Y('close:Q', scale=alt.Scale(zero=False)),
        tooltip=['date', 'close', 'volume']
    )
    
    # Volume Bar Chart
    bar = base.mark_bar(opacity=0.3).encode(
        y=alt.Y('volume:Q', axis=alt.Axis(title='Volume')),
        color=alt.value('gray')
    )
    
    st.altair_chart((line + bar).interactive(), use_container_width=True)

with tab3:
    st.header("Evaluation Metrics")
    
    # Lookback Tool
    st.subheader("🗓️ Look-back Analysis")
    days_back = st.slider("Target Date Lookback (Days Ago)", 3, 30, 7)
    target_dt = (datetime.now() - pd.Timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    st.caption(f"Analyzing predictions that targeted: **{target_dt}**")
    
    # Filter evals for this target date
    # Note: We need to join preds to get target_date if not present in evals fully, 
    # but let's assume simple filtering for now or use the DB logic logic roughly here
    
    # In dashboard we loaded raw tables. 
    # Let's filter predictions that had this target_date and join with evals
    target_preds = preds[preds['target_date'] == target_dt]
    
    if len(target_preds) == 0:
        st.warning(f"No predictions found targeting {target_dt}")
    else:
        # Check if they have evaluations
        relevant_evals = evals[evals['prediction_id'].isin(target_preds['id'])]
        
        if len(relevant_evals) > 0:
            acc = (relevant_evals['was_correct'].sum() / len(relevant_evals)) * 100
            st.metric("Batch Accuracy", f"{acc:.1f}%", f"{len(relevant_evals)} evaluated")
            
            st.dataframe(relevant_evals[['symbol', 'agent_name', 'prediction', 'actual_outcome', 'was_correct', 'actual_change_pct']])
        else:
            st.info("Predictions exist but haven't been evaluated yet (or data missing). Run `python evaluate.py`")
            st.dataframe(target_preds)

# Sidebar
st.sidebar.markdown("### ℹ️ About")
st.sidebar.info("Xmore2 is a hobby-grade system for the EGX. Use for educational purposes only.")
st.sidebar.markdown("---")
st.sidebar.caption("v2.1 Enhanced")
