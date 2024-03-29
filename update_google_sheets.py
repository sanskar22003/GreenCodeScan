import gspread
from oauth2client.service_account import ServiceAccountCredentials
import csv
import pandas as pd

# Use the credentials file you downloaded when setting up the Google Sheets API
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(r'C:\Users\sansk\Downloads\evocative-shore-417308-e617b5ec9771.json', scope)
client = gspread.authorize(creds)

# Open the Google Sheets document and get the first sheet
sheet1 = client.open("Dynamic_Code_Analysis").get_worksheet(0)
sheet2 = client.open("Server_Tracking_emissions").get_worksheet(0)

# Read the CSV and Excel files
csv_file = r'C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline\emissions_data.csv'
excel_file = r'C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline\server_data.xlsx'
sheets = [sheet1, sheet2]

# Read the CSV file
# Read the CSV file
with open(csv_file, 'r', encoding='utf-8') as f:
    csv_reader = csv.reader(f)
    rows = list(csv_reader)
    # Append all rows (excluding the header) to the Google Sheets document at once
    sheets[0].append_rows(rows[1:])

# Read the Excel file
df = pd.read_excel(excel_file)
# Append all rows (excluding the header) to the Google Sheets document at once
sheets[1].append_rows(df.values.tolist()[1:])
