import sqlite3
import pandas as pd

conn = sqlite3.connect("bookings.db")

# ---- call_requests Table ----
print("📞 Call Requests Table:\n")
call_df = pd.read_sql_query("SELECT * FROM call_requests LIMIT 10;", conn)
print("Columns:", list(call_df.columns))
print(call_df.head(10))  # Show first 10 rows of data

# ---- appointments Table ----
print("\n📅 Appointments Table:\n")
appt_df = pd.read_sql_query("SELECT * FROM appointments LIMIT 10;", conn)
print("Columns:", list(appt_df.columns))
print(appt_df.head(10))  # Show first 10 rows of data

conn.close()
