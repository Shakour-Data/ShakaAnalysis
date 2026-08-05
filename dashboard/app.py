#!/usr/bin/env python3
"""
Financial Dashboard - Interactive visualization for market data
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
import json

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'market_data.db')

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_symbols():
    """Load all symbols from database"""
    conn = get_db_connection()
    query = "SELECT symbol, name, type, exchange, industry FROM symbols WHERE is_active = 1 ORDER BY symbol"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def load_price_data(symbol=None, start_date=None, end_date=None):
    """Load price data with optional filters"""
    conn = get_db_connection()
    
    query = """
        SELECT p.*, s.symbol, s.name as symbol_name, s.type, s.exchange, s.industry
        FROM price_data p
        JOIN symbols s ON p.symbol_id = s.id
        WHERE s.is_active = 1
    """
    params = []
    
    if symbol:
        query += " AND s.symbol = ?"
        params.append(symbol)
    
    if start_date:
        query += " AND p.date >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND p.date <= ?"
        params.append(end_date)
    
    query += " ORDER BY p.date"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def create_price_chart(df, symbol_name):
    """Create interactive price chart"""
    if df.empty:
        return go Figure()
    
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=('Price', 'Volume', 'Technical Indicators'),
        row_width=[0.6, 0.2, 0.2]
    )
    
    # Price candlestick
    fig.add_trace(
        go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="Price"
        ),
        row=1, col=1
    )
    
    # Volume
    fig.add_trace(
        go.Bar(
            x=df['date'],
            y=df['volume'],
            name="Volume",
            marker_color='rgba(0, 150, 255, 0.6)'
        ),
        row=2, col=1
    )
    
    # Technical indicators (if available)
    if 'sma_20' in df.columns and not df['sma_20'].isna().all():
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['sma_20'],
                name="SMA 20",
                line=dict(color='orange', width=1)
            ),
            row=3, col=1
        )
    
    if 'sma_50' in df.columns and not df['sma_50'].isna().all():
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['sma_50'],
                name="SMA 50",
                line=dict(color='red', width=1)
            ),
            row=3, col=1
        )
    
    if 'rsi' in df.columns and not df['rsi'].isna().all():
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['rsi'],
                name="RSI",
                line=dict(color='purple', width=1)
            ),
            row=3, col=1
        )
        # Add RSI levels
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
    
    fig.update_layout(
        title=f"{symbol_name} - Financial Analysis",
        xaxis_rangeslider_visible=False,
        height=800,
        showlegend=True
    )
    
    fig.update_yaxes(title_text="Price (IRR)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_yaxes(title_text="Indicators", row=3, col=1)
    
    return fig

def main():
    st.set_page_config(
        page_title="Iran Financial Market Dashboard",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("🇮🇷 Iran Financial Market Dashboard")
    st.markdown("*Real-time data from Tehran Stock Exchange and OTC markets*")
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Load symbols
    symbols_df = load_symbols()
    
    # Symbol search
    search_term = st.sidebar.text_input("🔍 Search Symbol", placeholder="Enter symbol or name...")
    if search_term:
        filtered_symbols = symbols_df[
            symbols_df['symbol'].str.contains(search_term, case=False) |
            symbols_df['name'].str.contains(search_term, case=False)
        ]
    else:
        filtered_symbols = symbols_df
    
    # Symbol selection
    if not filtered_symbols.empty:
        symbol_options = filtered_symbols.apply(
            lambda row: f"{row['symbol']} - {row['name']}", axis=1
        ).tolist()
        selected_symbol_display = st.sidebar.selectbox(
            "Select Symbol",
            options=symbol_options,
            index=0 if symbol_options else None
        )
        
        if selected_symbol_display:
            selected_symbol = selected_symbol_display.split(' - ')[0]
            
            # Date range selection
            st.sidebar.subheader("📅 Date Range")
            date_option = st.sidebar.radio(
                "Date Range",
                ["Last 7 days", "Last 30 days", "Last 90 days", "Custom"],
                index=1
            )
            
            end_date = datetime.now().date()
            if date_option == "Last 7 days":
                start_date = end_date - timedelta(days=7)
            elif date_option == "Last 30 days":
                start_date = end_date - timedelta(days=30)
            elif date_option == "Last 90 days":
                start_date = end_date - timedelta(days=90)
            else:
                start_date = st.sidebar.date_input(
                    "Start Date",
                    value=end_date - timedelta(days=30)
                )
                end_date = st.sidebar.date_input(
                    "End Date",
                    value=end_date
                )
            
            # Load data
            with st.spinner("Loading data..."):
                df = load_price_data(
                    symbol=selected_symbol,
                    start_date=start_date.strftime('%Y-%m-%d') if isinstance(start_date, datetime) else start_date,
                    end_date=end_date.strftime('%Y-%m-%d') if isinstance(end_date, datetime) else end_date
                )
            
            if not df.empty:
                symbol_name = df['symbol_name'].iloc[0] if 'symbol_name' in df.columns else selected_symbol
                
                # Main chart
                st.subheader(f"📊 {symbol_name} ({selected_symbol})")
                fig = create_price_chart(df, symbol_name)
                st.plotly_chart(fig, use_container_width=True)
                
                # Data table
                with st.expander("📋 View Raw Data"):
                    display_df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'value']].copy()
                    display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
                    st.dataframe(
                        display_df.sort_values('date', ascending=False),
                        use_container_width=True,
                        height=400
                    )
                
                # Statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Latest Price", f"{df['close'].iloc[-1]:,.0f} IRR")
                with col2:
                    change = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
                    st.metric("Change", f"{change:+.2f}%", delta=f"{change:+.2f}%")
                with col3:
                    st.metric("Avg Volume", f"{df['volume'].mean():,.0f}")
                with col4:
                    st.metric("Data Points", len(df))
                
                # Export section
                st.subheader("💾 Export Data")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("📥 Export as CSV"):
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name=f"{selected_symbol}_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                
                with col2:
                    if st.button("📥 Export as JSON"):
                        json_str = df.to_json(orient='records', date_format='iso')
                        st.download_button(
                            label="Download JSON",
                            data=json_str,
                            file_name=f"{selected_symbol}_{datetime.now().strftime('%Y%m%d')}.json",
                            mime="application/json"
                        )
                
                with col3:
                    if st.button("📥 Export as Excel"):
                        # For Excel, we'd need openpyxl or xlsxwriter
                        # For now, show instructions
                        st.info("Excel export requires additional packages. Use CSV or JSON for now.")
            else:
                st.warning(f"No data found for {selected_symbol} in the selected date range.")
    else:
        st.warning("No symbols found matching your search criteria.")
    
    # Market overview
    st.sidebar.header("📈 Market Overview")
    if st.sidebar.button("Refresh Market Stats"):
        conn = get_db_connection()
        stats = conn.execute("""
            SELECT 
                COUNT(*) as total_symbols,
                SUM(CASE WHEN type = 'Stock' THEN 1 ELSE 0 END) as stocks,
                SUM(CASE WHEN type = 'Index' THEN 1 ELSE 0 END) as indices,
                SUM(CASE WHEN exchange = 'TSE' THEN 1 ELSE 0 END) as tse,
                SUM(CASE WHEN exchange = 'OTC' THEN 1 ELSE 0 END) as otc
            FROM symbols WHERE is_active = 1
        """).fetchone()
        conn.close()
        
        if stats:
            st.sidebar.metric("Total Symbols", stats[0])
            st.sidebar.metric("Stocks", stats[1])
            st.sidebar.metric("Indices", stats[2])
            st.sidebar.metric("TSE Market", stats[3])
            st.sidebar.metric("OTC Market", stats[4])

if __name__ == "__main__":
    main()