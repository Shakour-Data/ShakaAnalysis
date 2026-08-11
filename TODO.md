# TODO.md - Complete Project Operationalization Plan

## Documentation
- [ ] Update README.md with full installation guide (UTF-8 setup, Python 3.13+, DB path)
- [ ] Add API documentation (Swagger/OpenAPI spec for all endpoints)
- [ ] Write user manual for front-end dashboard (Persian UI instructions)
- [ ] Create developer guide covering folder structure and module responsibilities

## Database Preparation
- [ ] Populate `symbols` table with all 93 active Persian symbols (use verified list)
- [ ] Insert FARAZ symbol entry matching test expectations (symbol='FARAZ', name='فارس')
- [ ] Add comprehensive price_data for all symbols (1000+ rows per symbol)
- [ ] Populate indices tables (indices, industry_indices) with realistic market data
- [ ] Run `db_check.py` to verify schema integrity and row counts
- [ ] Back up initial database state to `data/backup_*.db`

## Backend Validation
- [ ] Fix `/api/indices` endpoint response format to match test schema
- [ ] Add `/api/price-data/<symbol>` endpoint (already implemented) 
- [ ] Ensure all API responses use UTF-8 encoding consistently
- [ ] Add proper error handling for missing symbols (404 with Persian message)
- [ ] Implement rate limiting for high-frequency API calls
- [ ] Add comprehensive unit tests for all new API endpoints
- [ ] Verify all Flask routes pass existing test suite (28 passed, 19 failed -> fix failures)

## Frontend Integration
- [ ] Configure `main.js` to support dynamic symbol loading from API
- [ ] Add fallback symbol list if API symbols endpoint fails
- [ ] Ensure chart data processing matches backend JSON structure
- [ ] Implement proper handling of UTC timestamps in charts
- [ ] Add error messages in Persian for all API failure cases
- [ ] Test all UI interactions: symbol search, date range, chart type, downloads
- [ ] Validate RTL layout renders correctly on all screen sizes

## Data Validation
- [ ] Run price indicator calculations (RSI, MACD, etc.) to verify data accuracy
- [ ] Compare generated CSV outputs against manual calculations
- [ ] Validate all indicators populate correctly in indicator cards
- [ ] Ensure download endpoints generate UTF-8 encoded CSV files
- [ ] Cross-check database row counts against expected test values

## Testing & Quality Assurance
- [ ] Execute full test suite: `python -m pytest tests/test_comprehensive.py -v`
- [ ] Achieve 100% test pass rate after fixing remaining failures
- [ ] Perform manual UI testing with real Persian symbols
- [ ] Validate all download functionality (price, indicators, full data)
- [ ] Conduct accessibility audit for Persian RTL layout
- [ ] Optimize performance for slow connections (lazy loading, pagination)

## Deployment
- [ ] Create production-ready `requirements.txt` pinning stable versions
- [ ] Configure `Procfile` for Heroku/PM2 deployment
- [ ] Set up environment variable handling (SECRET_KEY, DB_PATH)
- [ ] Implement SSL bypass for intranet SSL errors
- [ ] Prepare Dockerfile for containerized deployment
- [ ] Document startup commands (`npm run dev`, `python run.py`)

## Final Checks
- [ ] Verify `git remote` connections are configured
- [ ] Clean up temporary files across `outputs/`, `logs/`, `test_*`
- [ ] Confirm `final_verification.py` passes all validation checks
- [ ] Schedule daily data update script (`daily_update.py`) for production
- [ ] Enable production logging with rotation (`logging.config`)