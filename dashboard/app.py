import sqlite3
import pandas as pd
import sqlite3
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State
import plotly.express as px
import plotly.graph_objects as go

DB_PATH = 'data/market_data.db'

def read_db(query, params=None):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_symbols():
    df = read_db("SELECT symbol, name FROM symbols WHERE type = 'Stock'")
    return [{k: v for k, v in row.items()} for _, row in df.iterrows()]

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Shaka Analysis Dashboard", style={'textAlign': 'center'}),
    dcc.Tabs([
        dcc.Tab(label='Indices', children=[
            html.Div([
                dcc.Graph(id='tipex-graph'),
                dcc.Graph(id='tedpix-graph')
            ])
        ]),
        dcc.Tab(label='Stock Analysis', children=[
            html.Div([
                dcc.Dropdown(
                    id='symbol-dropdown',
                    options=[{'label': f"{s['symbol']} - {s['name']}", 'value': s['symbol']} 
                             for s in get_symbols()],
                    value=get_symbols()[0]['symbol'] if get_symbols() else None
                ),
                dcc.Graph(id='price-chart'),
                dcc.Graph(id='rsi-chart'),
                dcc.Graph(id='volume-chart')
            ])
        ])
    ]),
    dcc.Interval(id='interval', interval=300000)
])

@app.callback(
    [Output('tipex-graph', 'figure'),
     Output('tedpix-graph', 'figure')],
    Input('interval', 'n')
)
def update_indices(n):
    tipex_df = read_db('''
        SELECT date, close FROM indices 
        WHERE symbol = '30201' 
        ORDER BY date DESC LIMIT 365
    ''')
    fig_tipex = px.line(tipex_df, x='date', y='close', title='TEPIX Index (Last Year)')

    tedpix_df = read_db('''
        SELECT date, close FROM indices 
        WHERE symbol = '20101' 
        ORDER BY date DESC LIMIT 365
    ''')
    fig_tedpix = px.line(tedpix_df, x='date', y='close', title='TEDPIX Index (Last Year)')
    fig_tedpix = go.Figure(data=go.Scatter(x=tedpix_df['date'], y=tedpix_df['close'], 
                           mode='lines+markers', name='TEDPIX'))
    fig_tedpix.add_trace(go.Scatter(x=tedpix_df['date'], y=tedpix_df['close'].rolling(20).mean(),
                                    mode='lines', name='20-Day MA'))
    fig_tedpix.update_layout(title='TEDPIX Index with Moving Average')
    return fig_tipex, fig_tedpix

@app.callback(
    [Output('price-chart', 'figure'),
     Output('rsi-chart', 'figure'),
     Output('volume-chart', 'figure')],
    [Input('symbol-dropdown', 'value'),
     Input('interval', 'n')]
)
def update_stock_charts(symbol, n):
    if not symbol:
        return {}, {}, {}
    
    df = read_db('''
        SELECT date, open, high, low, close, volume, rsi, sma_20, sma_50
        FROM price_data p
        JOIN symbols s ON p.symbol_id = s.id
        WHERE s.symbol = ?
        ORDER BY date DESC LIMIT 100
    ''', (symbol,))
    
    fig_price = go.Figure()
    fig_price.add_trace(go.Candlestick(x=df['date'],
                    open=df['open'], high=df['high'],
                    low=df['low'], close=df['close'],
                    name='Price'))
    fig_price.add_trace(go.Scatter(x=df['date'], y=df['sma_20'], 
                  mode='lines', name='SMA20'))
    fig_price.add_trace(go.Scatter(x=df['date'], y=df['sma_50'], 
                  mode='lines', name='SMA50'))
    fig_price.update_layout(title=f'{symbol} Price Chart', xaxis_title='Date',
                            yaxis_title='Price')
    
    fig_rsi = px.line(df, x='date', y='rsi', title=f'{symbol} RSI')
    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
    
    fig_vol = px.bar(df, x='date', y='volume', title=f'{symbol} Volume')
    
    return fig_price, fig_rsi, fig_vol

if __name__ == '__main__':
    app.run_server(debug=True)