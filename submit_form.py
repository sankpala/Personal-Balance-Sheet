# -*- coding: utf-8 -*-
"""Submit Form.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/16fsyVD49Rejxnd7UIYpzxRSOmzbalkMl
"""

pip install selenium

pip install psycopg2-binary

import sys
import os
from selenium import webdriver
import time
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd
import pytz
import psycopg2
import urllib.parse


chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(options=chrome_options)



url = "https://ha2x0yyn.forms.app/tripplanning/report/datas/1"
# Open the URL
driver.get(url)
# Wait for 10 seconds for the page to load
time.sleep(10)
# Get the page source
page_source = driver.page_source

soup = BeautifulSoup(page_source, 'html.parser')
# Find the table
table = soup.find('table')

col=[]
rows = table.find_all('thead')
# Iterate through each row
for row in rows:
    # Find all cells in the row
    cells = row.find_all('th')
    for cell in cells:
      col.append(cell.text)

body=table.find_all('tbody')

df_list=[]
for rbody in body:
    cellbody = rbody.find_all('tr')
    for f in cellbody:
        cell2 = f.find_all('td')
        df_obj={}
        h=0
        for cell in cell2:
            # Get all the text within the cell and join with '/'
            cell_texts = [text for text in cell.stripped_strings]
            df_obj[col[h]]=cell_texts
            h=h+1
        df_list.append(df_obj)

def to_df(df_list,keys_to_keep):
  h=[]
  for y in df_list:
    y['sepContri_1']=y['Seperate Contribution-1']
    y['sepContri_2']=y['Seperate Contribution-2']
    y['sepContri_3']=y['Seperate Contribution-3']
    y['sepContri_4']=y['Seperate Contribution-4']
    y['sepContri_5']=y['Seperate Contribution-5']
    y['payer']=y['Who Paid Money'][0]
    y['payerAmt']=y['How much'][0]
    y['reason']=y['Reason of Spend'][0] if y['Reason of Spend'] else None
    y['submissionDate']=y['Submission Date'][0]
    y['tripName']=y['TripName'][0] if y['TripName'] else None
    y['contri']=y['Who included in the Contribution?']
    filtered_dict = {key: y[key] for key in keys_to_keep if key in y}
    h.append(filtered_dict)
  df=pd.DataFrame(h)
  return df

df1=to_df(df_list,['payer','payerAmt','reason','submissionDate','tripName','sepContri_1','sepContri_2','sepContri_3','sepContri_4','sepContri_5'])

df2=to_df(df_list,['payer','payerAmt','reason','submissionDate','tripName','contri'])

melted_df = pd.melt(df1, id_vars=['payer', 'payerAmt', 'reason', 'submissionDate', 'tripName'],
                    value_vars=['sepContri_1', 'sepContri_2', 'sepContri_3', 'sepContri_4', 'sepContri_5'],
                    var_name='Contribution', value_name='Value')

melted_df = melted_df[melted_df['Value'].apply(lambda x: x != [])]

melted_df[['contri', 'contriAmt']] = pd.DataFrame(melted_df['Value'].tolist(), index=melted_df.index)

# Dropping the original 'Value' column
melted_df = melted_df.drop(columns=['Value']).copy()

melted_df = melted_df.loc[:, ['payer', 'payerAmt', 'reason', 'submissionDate', 'tripName', 'contri', 'contriAmt']].reset_index(drop=True)



melted_df2 = df2.explode('contri')

melted_df['contriAmt'] = melted_df['contriAmt'].astype(int)
grouped_df1 = melted_df.groupby(['payer', 'payerAmt', 'reason', 'submissionDate', 'tripName'])['contriAmt'].sum().reset_index()



grouped_df2 = melted_df2.groupby(['payer', 'payerAmt', 'reason', 'submissionDate', 'tripName'])['contri'].nunique().reset_index()

grouped_df3 = pd.merge(grouped_df2, grouped_df1, on=['payer', 'payerAmt', 'reason', 'submissionDate', 'tripName'], how='left')

grouped_df3['payerAmt']=grouped_df3['payerAmt'].astype(int)
grouped_df3['splitAmt'] = grouped_df3['payerAmt'].fillna(0) - grouped_df3['contriAmt'].fillna(0)
grouped_df3['devideAmt']=grouped_df3['splitAmt']/grouped_df3['contri'].fillna(1)

grouped_df3=grouped_df3.loc[:,['payer', 'payerAmt', 'reason', 'submissionDate', 'tripName','devideAmt']].reset_index(drop=True)



melted_df2['payerAmt'] = melted_df2['payerAmt'].astype(int)

melted_df2 = pd.merge(melted_df2, grouped_df3, on=['payer', 'payerAmt', 'reason', 'submissionDate', 'tripName'], how='left')

melted_df2 = melted_df2.rename(columns={'devideAmt': 'contriAmt'})



melted_df['payerAmt'] = melted_df['payerAmt'].astype(int)
melted_df['contriAmt'] = melted_df['contriAmt'].astype(float)

df_final = pd.concat([melted_df2,melted_df]).reset_index(drop=True)

# Create copies of the DataFrame
df_final1 = df_final.copy()
df_final2 = df_final.copy()

# Add 'Flag' column to each DataFrame
df_final1['Flag'] = 'Spend'
df_final2['Flag'] = 'Expense'

# Concatenate the DataFrames
df_final = pd.concat([df_final1, df_final2]).reset_index(drop=True)

ist = pytz.timezone('Asia/Kolkata')

# Current IST timestamp
current_time = datetime.now(ist)

# Add 'Last_Refresh_Date' with the current IST timestamp
df_final['Last_Refresh_Date'] = current_time

# Date formats
date_format = "%m/%d/%Y, %I:%M:%S %p"
output_format = "%Y-%m-%d %H:%M:%S"

# Convert 'submissionDate' to datetime if it's a string, then format to desired output
def convert_submission_date(x):
    if isinstance(x, str):
        x = datetime.strptime(x, date_format)
    return x.strftime(output_format)

df_final['submissionDate'] = df_final['submissionDate'].apply(convert_submission_date)

# Convert 'Last_Refresh_Date' to the desired string format
df_final['Last_Refresh_Date'] = df_final['Last_Refresh_Date'].apply(lambda x: x.strftime(output_format))

# Define your connection parameters
db_user = 'admin'
db_password = 'sheffzku34-hiC1e_0ekvRwMw4SeGo'
hostname = 'us-east-1.766380d8-b7db-42bf-b16e-6f787b7cfac8.aws.ybdb.io'
port = '5433'
database = 'yugabyte'
#sslmode = 'verify-full'
#sslrootcert = '/content/root.crt'  # Replace with your actual CA certificate path

# URL encode the password if it contains special characters
db_password = urllib.parse.quote_plus(db_password)

# Construct the connection string
conn_string = f"postgresql://{db_user}:{db_password}@{hostname}:{port}/{database}"
conn = psycopg2.connect(conn_string)
print("Connection to the database established successfully.")
# Create a cursor object
cur = conn.cursor()

# Close the cursor and the connection
#cur.close()
#conn.close()
#print("Database connection closed.")

def get_data(cur,query):
  cur.execute(query)
  colnames = [desc[0] for desc in cur.description]
  rows = cur.fetchall()
  return pd.DataFrame([dict(zip(colnames, row)) for row in rows])


def create_table(df,sql_table_name,cur,conn):
  # Map Pandas data types to PostgreSQL data types
  dtype_mapping = {
      'int64': 'INTEGER',
      'float64': 'FLOAT',
      'object': 'TEXT',
      # Add more mappings as needed
  }
  # Extract column names and their corresponding data types
  columns_info = ", ".join([f"{column} {dtype_mapping[str(df[column].dtype)]}" for column in df.columns])

  # Generate SQL query for table creation
  create_table_query = f"CREATE TABLE IF NOT EXISTS {sql_table_name} ({columns_info});"
  conn.rollback()
  conn.commit()
  cur.execute(create_table_query)
  return create_table_query

def delete_data_from_table(table_name, cur, conn):
    # Generate SQL query for deleting all data from the table
    delete_data_query = f"DELETE FROM {table_name};"

    try:
        # Execute the delete query
        cur.execute(delete_data_query)
        conn.commit()
    except Exception as e:
        # If there's an error, rollback the transaction and re-raise the exception
        conn.rollback()
        raise e

def write_table(df, table_name, cur, conn):
    try:
        # Start a transaction
        cur.execute("BEGIN;")

        # Prepare the INSERT statement
        placeholders = ', '.join(['%s'] * len(df.columns))
        columns = ', '.join(df.columns)
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders});"

        # Extract values from DataFrame as a list of tuples
        values = [tuple(row) for row in df.values]

        # Execute the INSERT statement with executemany()
        cur.executemany(sql, values)

        # Commit the transaction
        conn.commit()
    except Exception as e:
        # If any error occurs, rollback the transaction
        conn.rollback()
        print("Error:", e)

create_table(df_final,'trip_plan',cur,conn)

delete_data_from_table('trip_plan',cur,conn)

write_table(df_final,'trip_plan',cur,conn)

cur.close()
conn.close()