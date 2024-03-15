import gspread
from oauth2client.service_account import ServiceAccountCredentials
import csv

# Use the credentials file you downloaded when setting up the Google Sheets API
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(r'C:\Users\sansk\Downloads\evocative-shore-417308-e617b5ec9771.json', scope)
client = gspread.authorize(creds)

# Open the Google Sheets document and get the first sheet
sheet1 = client.open("Dynamic_Code_Analysis").get_worksheet(0)
sheet2 = client.open("Server_Tracking_emissions").get_worksheet(0)

# Read the CSV files
csv_files = [r'C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline\emissions_data.csv', r'C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline\server_data.xlsx']
sheets = [sheet1, sheet2]

for csv_file, sheet in zip(csv_files, sheets):
    with open(csv_file, 'r') as f:
        csv_reader = csv.reader(f)
        for row in csv_reader:
            # Append each row to the Google Sheets document
            sheet.append_row(row)
