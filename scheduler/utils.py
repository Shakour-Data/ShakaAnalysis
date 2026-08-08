import win10toast

def notify_success(message):
    """Send a Windows toast notification for successful completion."""
    try:
        toast = win10toast.ToastNotifier()
        toast.show_toast("Shaka Analysis Update", message, duration=10)
    except Exception as e:
        print(f"Notification failed: {e}")

def notify_error(message):
    """Send a Windows toast notification for errors."""
    try:
        toast = win10toast.ToastNotifier()
        toast.show_toast("Shaka Analysis Error", message, duration=10)
    except Exception as e:
        print(f"Notification failed: {e}")

def notify_data_freshness():
    """Check and notify about data freshness."""
    try:
        import sqlite3
        conn = sqlite3.connect('data/market_data.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM price_data")
        count = c.fetchone()[0]
        conn.close()
        if count == 0:
            notify_error("No price data found in database!")
        else:
            notify_success(f"Database has {count} records. Data is up to date.")
    except Exception as e:
        notify_error(f"Data freshness check failed: {e}")