# Shaka Analysis Project

## Project Overview
A comprehensive financial data analysis platform for Persian stock market data (TSE/OTC). Handles:
- Daily price data extraction
- Technical indicator calculation (RSI, MACD, Bollinger Bands)
- Backtesting and risk analysis
- Correlation analysis
- Machine learning feature generation

## Key Features
- **Multi-Symbol Support**: Processes 1,289 symbols
- **Islamic Finance Integration**: Sharia-compliant data handling
- **Real-time Indicator Calculation**: Provides 12 technical indicators
- **Risk Management Tools**: Sharpe ratio, Sortino ratio, VaR analysis
- **Historical Analysis**: 6-month historical data tracking

## Directory Structure
```
project_root/
├── data/
├── src/
│   ├── database/  # Database utilities
│   ├── extraction/  # Data extraction logic
│   ├── analysis/  # Data analysis components
│   └── utils/  # Utility functions
├── outputs/
└── docs/

## Installation (UTF-8 Setup)

### System Requirements
- **Python**: 3.13+
- **Operating System**: Windows 10/11, Linux, or macOS
- **Database**: SQLite (comes with Python)

### Installation Steps

1. **Clone the repository**:
```bash
git clone <repository-url>
cd shaka-analysis
```

2. **Configure environment**:
```bash
# Create virtual environment (recommended)
python -m venv venv
# On Windows:
# venv\Scripts\activate
# On Linux/macOS:
# source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. **Set up database**:
```python
# Run database initialization
python -c "from src.database.database import init_database; init_database()"
```

### UTF-8 Configuration

**Windows**:
- Ensure Python is configured with UTF-8:
```python
import sys
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

**Linux/macOS**:
- UTF-8 is typically the default encoding

### Database Path Configuration

**Default Database Path**: `data/market_data.db`

**Environment Variables** (set these before running):
```bash
export DB_PATH="data/market_data.db"
export PYTHONPATH="src:$PYTHONPATH"
```

**Config File Example** (`config.py`):
```python
# config.py
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'market_data.db')
REQUIREMENTS_FILE = 'requirements.txt'
SSL_BYPASS_ENABLED = True
```

## Usage

### Basic Operations

**Daily Update**:
```python
python src/extraction/daily_update.py
```

**Full Analysis Pipeline**:
```python
python src/analysis/full_production_pipeline.py
```

**Extract Symbols**:
```python
python src/extraction/extract_symbols.py
```

### Command Line Interface

```bash
# Extract symbols
python extract_symbols.py

# Process prices
python extract_prices.py

# Run daily update
python daily_update.py

# Generate analysis
python full_production_pipeline.py
```

## Configuration

### SSL Bypass (For Intranet Access)

For accessing TSE (Iran Stock Exchange) which may have SSL issues, the platform automatically bypasses SSL verification:

```python
# auto-configures SSL bypass on startup
import ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
```

### Environment Setup

Create `.env` file:
```env
PYTHONIOENCODING=utf-8
DB_PATH=data/market_data.db
TZ=Asia/Tehran
```

## Project Structure

### Source Code Layout

```
src/
├── database/                    # Database operations
│   ├── __init__.py
│   ├── database.py              # Connection management
│   └── populate_database.py     # Data population
├── extraction/                  # Data extraction
│   ├── __init__.py
│   ├── extract_symbols.py       # Symbol extraction
│   ├── extract_prices.py        # Price extraction
│   └── daily_update.py          # Daily updates
├── analysis/                    # Analysis logic
│   ├── __init__.py
│   ├── indicators.py            # Technical indicators
│   ├── risk_analysis.py         # Risk calculations
│   └── ml_features.py           # ML feature generation
└── utils/                       # Utility functions
    ├── __init__.py
    ├── ssl_utils.py              # SSL handling
    ├── date_utils.py             # Date utilities
    └── file_utils.py             # File operations
```

### Data Structure

```
data/
├── market_data.db              # SQLite database
├── cache/                      # Temporary cache files
├── extracted_symbols.json       # Raw symbol data
└── price_cache/                # Price data cache
```

### Output Structure

```
outputs/
├── daily_updates/              # Daily update outputs
├── backtest/                   # Backtesting results
├── indicators/                 # Indicator calculations
├── risk_metrics/               # Risk analysis results
├── correlation/                # Correlation matrices
├── ml_features/                # ML feature matrices
├── reports/                    # Analysis reports
└── scheduler_config.txt        # Scheduler configuration
```

## API Endpoints

### REST API

Base URL: `http://localhost:5000/api`

**Available Endpoints**:
- `GET /api/symbols` - Get all symbols
- `GET /api/price/{symbol}` - Get price data for symbol
- `GET /api/price-data/{symbol}` - Get full price data for symbol
- `GET /api/indices` - Get index data
- `POST /api/analysis/save` - Save analysis results

**Example Usage**:
```bash
# Get all symbols
curl "http://localhost:5000/api/symbols"

# Get price data for a symbol
curl "http://localhost:5000/api/price/فولاد"
```

## Development

### Testing

Run the full test suite:
```bash
python -m pytest tests/ -v
```

### Running from Source

```bash
# Set up Python path
export PYTHONPATH="src:$PYTHONPATH"

# Run a specific module
python -m src.extraction.extract_symbols
```

### Adding New Symbols

1. Add symbol to `extracted_symbols.json`:
```json
{"symbol": "NEW", "name": "New Company", "type": "Stock", "exchange": "TSE"}
```

2. Run symbol extractor:
```bash
python src/extraction/extract_symbols.py
```

## Deployment

### Local Deployment

```bash
# Install and run full pipeline
pip install -r requirements.txt
python src/analysis/full_production_pipeline.py
```

### Production Deployment

1. **Docker**:
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "src/analysis/full_production_pipeline.py"]
```

2. **PM2**:
```bash
npm install pm2 -g
pm2 start ecosystem.config.js
```

### Kubernetes

See `k8s/` directory for Kubernetes manifests.

## Troubleshooting

### Common Issues

**Issue**: SSL certificate errors
**Solution**: Check if you're behind a proxy that requires SSL verification. The application has automatic SSL bypass for this reason.

**Issue**: Database file not found
**Solution**: Ensure the `data/` directory exists and has proper permissions.

**Issue**: Unicode encoding problems
**Solution**: Use UTF-8 in Python console and editors. Ensure `PYTHONIOENCODING=utf-8` environment variable is set.

**Issue**: Performance problems
**Solution**: Use the `outputs/` directory for storing large intermediate files. Configure the application to use memory-mapped files for better performance.

## Troubleshooting

### Common Issues

**Issue**: SSL certificate errors
**Solution**: The platform includes automatic SSL bypass for accessing TSE (Iran Stock Exchange). No additional configuration needed.

**Issue**: Database initialization errors
**Solution**: Ensure dependencies are installed. Try:
```bash
pip install -r requirements.txt
```

**Issue**: Unicode/encoding problems
**Solution**: Set UTF-8 encoding:
```bash
export PYTHONIOENCODING=utf-8
```

**Issue**: Path issues
**Solution**: Use absolute paths:
```python
import os
DB_PATH = os.path.abspath('data/market_data.db')
```

## Performance Optimization

### Large Database

For databases with many symbols:
- Use memory-mapped SQLite: `PRAGMA mmap_size = 268435456;`
- Batch operations for better performance
- Consider database partitioning by symbol type

### Slow Connections

- Enable caching for frequently accessed data
- Use connection pooling
- Implement lazy loading for large datasets

## License
MIT License

Copyright (c) 2026 Shaka Analysis Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR
IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
