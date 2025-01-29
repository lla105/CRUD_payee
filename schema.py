import pandas as pd

df = pd.read_csv('payment_information.csv')
print(df.columns)
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
df['payee_first_name'] = df['payee_first_name'].astype(str).str.strip().str.lower()
df['payee_last_name'] = df['payee_last_name'].astype(str).str.strip().str.lower()
df['payee_payment_status'] = df['payee_payment_status'].astype(str).str.strip().str.lower()
df["payee_added_date_utc"] = pd.to_datetime(df["payee_added_date_utc"], unit="s", utc=True)
df['payee_due_date'] = pd.to_datetime(df['payee_due_date']).dt.date
print(df['payee_due_date'])
