# Shaka Analysis - Developer Guide

## Project Structure Overview

```
shaka-analysis/
├── data/                          # Database and data files
│   ├── market_data.db             # Main SQLite database
│   ├── cache/                     # Cached HTML and symbol data
│   └── backup_*.db                # Database backups
├── docs/                          # Documentation
│   ├── openapi.yaml               # OpenAPI 3.0 specification
│   ├── finpy-tse.pdf              # finpy-tse library docs
│   └── README.md                  # Project documentation
├── outputs/                       # Generated analysis outputs
│   ├── all_symbols_backtest.csv
│   ├── all_screener_signals.csv
│   ├── all_risk_metrics.csv
│   ├── correlation_matrix_full.csv
│   ├── high_correlation_pairs.csv
│   ├── all_ml_features.csv
│   ├── daily_update.py
│   ├── scheduler_config.txt
│   └── complete_analysis_report.txt
├── reports/                       # Generated reports
│   └── *.xlsx, *.html
├── logs/                          # Application logs
├── frontend/                      # Frontend dashboard
│   ├── index.html                 # Main dashboard (RTL Persian)
│   └── js/
│       └── main.js                # Frontend logic
├── api/                           # Flask REST API
│   ├── app.py                     # Main Flask application
│   ├── serve_api.py               # API server entry point
│   └── start_api.bat              # Windows startup script
├── dashboard/                     # Dash-based dashboard
│   ├── app.py                     # Dash application
│   └── serve_dashboard.py         # Dashboard server
├── src/                           # Main source code
│   ├── __init__.py
│   ├── extraction/                # Data extraction modules
│   │   ├── __init__.py
│   │   ├── extract_symbols.py     # Symbol extraction from TSE
│   │   ├── extract_prices.py      # Price data extraction
│   │   ├── step1_load_symbols.py  # Step 1: Load symbols
│   │   ├── step2_extract_prices.py # Step 2: Extract prices
│   │   ├── get_all_symbols_data.py # Get all symbols data
│   │   ├── final_extract.py       # Final extraction
│   │   └── daily_update.py        # Daily data updates
│   ├── analysis/                  # Data analysis modules
│   │   ├── __init__.py
│   │   ├── indicators.py          # Technical indicators
│   │   ├── risk_analysis.py       # Risk metrics
│   │   ├── ml_features.py         # ML feature generation
│   │   └── full_production_pipeline.py # Full pipeline
│   ├── utils/                     # Utility functions
│   │   ├── __init__.py
│   │   ├── ssl_utils.py           # SSL bypass utilities
│   │   ├── date_utils.py          # Date conversion
│   │   └── file_utils.py          # File operations
│   └── database/                  # Database utilities
│       ├── __init__.py
│       ├── database.py            # Schema initialization
│       ├── populate_comprehensive.py # Populate with sample data
│       ├── populate_database.py   # Basic population
│       └── populate_db.py         # Alternative population
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── test_comprehensive.py      # Comprehensive tests
│   ├── test_symbols.py            # Symbol tests
│   ├── test_indicators.py         # Indicator tests
│   └── test_data.py               # Data tests
├── scheduler/                     # Scheduling utilities
│   ├── utils.py                   # Scheduler utilities
│   ├── run_daily.bat              # Daily run script
│   ├── db_monitor.py              # Database monitoring
│   └── db_backup.py               # Database backup
└── requirements.txt               # Python dependencies
```

## Module Responsibilities

### src/database/
- **database.py**: Database schema initialization, connection management
- **populate_comprehensive.py**: Populate database with realistic sample data for all tables
- **populate_database.py**: Basic database population
- **populate_db.py**: Alternative population method

### src/extraction/
- **extract_symbols.py**: Extract stock symbols from TSE HTML
- **extract_prices.py**: Extract price history using finpy-tse
- **step1_load_symbols.py**: First step in ETL pipeline - load symbols
- **step2_extract_prices.py**: Second step - extract price data
- **get_all_symbols_data.py**: Get comprehensive data for all symbols
- **final_extract.py**: Final extraction with indicators
- **daily_update.py**: Daily incremental update script

### src/analysis/
- **indicators.py**: Technical indicator calculations (RSI, MACD, Bollinger Bands, etc.)
- **risk_analysis.py**: Risk metrics (Sharpe, Sortino, VaR, Max Drawdown)
- **ml_features.py**: Machine learning feature generation
- **full_production_pipeline.py**: Complete analysis pipeline

### src/utils/
- **ssl_utils.py**: SSL context configuration for intranet access
- **date_utils.py**: Date conversion utilities (Jalali/Gregorian)
- **file_utils.py**: File I/O utilities

### api/
- **app.py**: Flask REST API with endpoints:
  - GET /api/symbols - All active symbols
  - GET /api/data/<symbol> - Price data with indicators
  - GET /api/indices - Market indices
  - GET /api/price/<symbol> - Summary price data
  - GET /api/price-data/<symbol> - Full price data
  - POST /api/analysis/save - Save analysis
  - GET /api/download/<symbol>/<type> - Download CSV

### frontend/
- **index.html**: RTL Persian dashboard with Chart.js
- **js/main.js**: Frontend logic for API integration

### dashboard/
- **app.py**: Dash-based interactive dashboard

## Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  TSE HTML   │────▶│  Extract    │────▶│  Database   │
│  / finpy-tse│     │  Symbols    │     │  (SQLite)   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                        ┌─────────────┐         │
                        │  Analysis   │◀────────┘
                        │  Pipeline   │
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │   Outputs   │
                        │  (CSV, etc) │
                        └─────────────┘
```

## Key Technical Details

### Database Schema
- **symbols**: Stock/index/currency metadata (id, symbol, name, type, exchange, industry, sector, etc.)
- **price_data**: OHLCV data with 20+ technical indicators
- **indices**: Market index data (TEPIX, TEDPIX, etc.)
- **industry_indices**: Industry index mappings
- **analysis_records**: Saved technical analysis
- **export_history**: Export audit trail
- **data_metadata**: Data quality tracking

### Technical Indicators Calculated
- SMA (9, 14, 20, 21, 35, 50, 100)
- RSI (9, 14, 21, 35)
- MACD (12,26,9 and 14-period)
- Bollinger Bands (20, 2)
- ADX (14)
- CCI (20)
- MFI (14)

### SSL Bypass
The platform uses a monkey-patched SSL context to bypass certificate verification for intranet access to TSE:
```python
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
```

### Date Handling
- Jalali dates stored as strings in database
- Conversion utilities in src/utils/date_utils.py

## Running the Project

### Prerequisites
- Python 3.13+
- SQLite (built-in)
- Dependencies from requirements.txt

### Start API Server
```bash
cd api
python app.py
# Runs on http://localhost:5000
```

### Run Daily Update
```bash
python src/extraction/daily_update.py
```

### Run Full Analysis Pipeline
```bash
python src/analysis/full_production_pipeline.py
```

### Run Tests
```bash
# Start API server first
python -m pytest tests/ -v
```

## Adding New Features

### Adding a New Technical Indicator
1. Add calculation function in src/analysis/indicators.py
2. Add column to price_data table in src/database/database.py
3. Update extraction scripts to compute and store the indicator
4. Add to API response in api/app.py
5. Add to frontend display in frontend/index.html

### Adding a New API Endpoint
1. Add route in api/app.py
2. Add OpenAPI documentation in docs/openapi.yaml
3. Add tests in tests/
4. Update frontend if needed

## Best Practices

1. **UTF-8 Encoding**: Always use UTF-8 for Persian text
2. **Error Handling**: Wrap external API calls in try/except
3. **Database Connections**: Use context managers or explicit close
4. **Rate Limiting**: Implement for high-frequency API calls
5. **Logging**: Use structured logging with rotation
6. **Testing**: Write tests for new endpoints and calculations

## Troubleshooting

### SSL Certificate Errors
Ensure SSL bypass is configured in src/utils/ssl_utils.py

### Database Locked
Enable WAL mode: `PRAGMA journal_mode=WAL`

### Missing Price Data
Check finpy-tse installation and SSL configuration

### Port Already in Use
Change port in api/app.py or kill existing process

## Contributing

1. Follow existing code style
2. Add tests for new functionality
3. Update documentation
4. Run full test suite before committing