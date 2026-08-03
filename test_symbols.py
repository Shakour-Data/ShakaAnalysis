import sys
sys.stdout.reconfigure(encoding='utf-8')
import finpy_tse as tse

# Get market watch data to find valid stock names/symbols
result = tse.Get_MarketWatch()
if isinstance(result, tuple):
    df = result[0]
    print("Market watch columns:", df.columns.tolist())
    print("\nFirst 10 stock names:")
    for i, row in df.head(10).iterrows():
        print(f"  {i}: Name='{row['Name']}', Sector='{row['Sector']}'")
    
    # Try a few known working symbols
    test_symbols = ['شركت صنايع گاز كرجايي', 'توسعه شهری توس گستر', 'بهمن دیزل', 
                    'فولاد', 'خودرو', 'خزف', 'پتروشیمی']
    
    print("\nTesting Get_Price_History with different symbols:")
    for sym in test_symbols:
        try:
            df_price = tse.Get_Price_History(
                stock=sym,
                start_date='2023-01-01',
                end_date='2024-01-01',
                adjust_price=True
            )
            if df_price is not None and not df_price.empty:
                print(f"  ✅ SUCCESS: '{sym}' -> {df_price.shape}")
                print(f"     Columns: {df_price.columns.tolist()}")
                break
            else:
                print(f"  ❌ EMPTY: '{sym}'")
        except Exception as e:
            print(f"  ❌ ERROR '{sym}': {str(e)[:150]}")