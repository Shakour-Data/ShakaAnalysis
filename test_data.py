import finpy_tse
import warnings
warnings.filterwarnings('ignore')

# Test available indices/symbols
indices = ['شاخص کل', 'شاخص قیمت', 'شاخص هم وزن', 'شاخص 30', 'شاخص 50', 'صنعت', 'دلار', 'سکه']
for idx in indices:
    try:
        df = finpy_tse.Get_Price_History(stock=idx, start_date='1403-01-01', end_date='1403-12-29', ignore_date=True, adjust_price=True)
        if len(df) > 0:
            print(f'{idx}: {len(df)} rows - Last close: {df["Adj Close"].iloc[-1]}')
    except Exception as e:
        print(f'{idx}: ERROR - {type(e).__name__}')