import pandas as pd
import pycountry

def normalize_data(df):
    text_fields = ['payee_first_name','payee_last_name','payee_payment_status', 
                   'payee_address_line_1', 'payee_address_line_2', 'payee_city', 
                   'payee_country', 'payee_province_or_state', 'payee_postal_code',
                   'payee_email', 'currency', 'discount_percent', 'tax_percent', 'due_amount']
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    for field in text_fields:
        df[field] = df[field].astype(str).str.strip().str.lower()
    df["payee_added_date_utc"] = pd.to_datetime(df["payee_added_date_utc"], unit="s", utc=True)
    df['payee_due_date'] = pd.to_datetime(df['payee_due_date']).dt.date
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


def main():
    df = pd.read_csv('payment_information.csv', keep_default_na=False, na_values=['_'])
    normalize_data(df)

main()
