import pandas as pd
import pycountry
from pymongo import MongoClient

def calculate_total_due(df):
    df['discount_percent'] = pd.to_numeric(df['discount_percent'], errors='coerce') 
    df['tax_percent'] = pd.to_numeric(df['tax_percent'], errors='coerce')  
    df['due_amount'] = pd.to_numeric(df['due_amount'], errors='coerce')
    df['discount'] = df['due_amount'] * df['discount_percent']/100
    df['tax'] = df['due_amount'] * df['tax_percent']/100
    df['total_due'] = df['due_amount'] - df['discount'] + df['tax']
    df['total_due'] = df['total_due'].round(2)
    df.drop( ['discount', 'tax'], axis=1, inplace=True) #drop discount and tax after use.
    return df

def normalize_data(df):
    text_fields = ['payee_first_name','payee_last_name','payee_payment_status', 
                   'payee_address_line_1', 'payee_address_line_2', 'payee_city', 
                   'payee_country', 'payee_province_or_state', 'payee_postal_code',
                   'payee_email', 'currency', 'discount_percent', 'tax_percent', 'due_amount']
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df = calculate_total_due(df)
    for field in text_fields:
        df[field] = df[field].astype(str).str.strip().str.lower()
    df["payee_added_date_utc"] = pd.to_datetime(df["payee_added_date_utc"], unit="s", utc=True)
    df['payee_due_date'] = pd.to_datetime(df['payee_due_date'], errors='coerce')
    if df['payee_address_line_1'].isnull().any():
        print('An Address 1 missing.')
    city_error =  df['payee_city'].isnull().any()
    if city_error.any() :
        print('Cities with errors: ', df[city_error]['payee_city'].tolist())

    df['payee_country'] = df['payee_country'].astype(str).str.strip().str.upper()
    valid_country_codes = set()
    for country in pycountry.countries:
        valid_country_codes.add(country.alpha_2)
    country_error = (df['payee_country'].isnull()) | (~df['payee_country'].isin(valid_country_codes) )
    if country_error.any() :
        print('Countries with errors:' , df[country_error]['payee_country'].tolist())
    df['payee_postal_code'] = df['payee_postal_code'].astype(str).str.strip().str.upper()
    return df

def connect_mongo(df):
    client = MongoClient('mongodb://localhost:27017/')
    db = client['CRUD']
    collection = db['payment_data']
    data_dict = df.to_dict(orient='records')
    if data_dict:
        collection.insert_many(data_dict)
        print(f"{len(data_dict)} records inserted.")
    else:
        print(f'no data inserted.')

        
def main():
    df = pd.read_csv('payment_information.csv', keep_default_na=False, na_values=['_'])
    normalized_df = normalize_data(df)
    connect_mongo(normalized_df)
main()
