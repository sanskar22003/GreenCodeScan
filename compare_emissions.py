import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.abspath(".env")
load_dotenv(dotenv_path=env_path, verbose=True, override=True)

# Remove the '.env' part to get the SOURCE_DIRECTORY
SOURCE_DIRECTORY = os.path.dirname(env_path)
result_source_dir = os.path.join(SOURCE_DIRECTORY, 'Result', 'main_before_emissions_data.csv')
result_green_refined_directory = os.path.join(SOURCE_DIRECTORY, 'Result', 'main_after_emissions_data.csv')
result_folder_path = os.path.join(SOURCE_DIRECTORY, 'Result')

# Read CSV files
emissions_df = pd.read_csv(result_source_dir)
emissions_after_df = pd.read_csv(result_green_refined_directory)

# Merge dataframes on common columns
merged_df = emissions_df.merge(emissions_after_df, on=["Application name", "File Type"], suffixes=('_before', '_after'))

# Calculate the difference in emissions and determine the result
merged_df['final emission'] = merged_df['Emissions (gCO2eq)_before'] - merged_df['Emissions (gCO2eq)_after']
merged_df['Result'] = merged_df['final emission'].apply(lambda x: 'Improved' if x > 0 else 'Need improvement')

# Select and rename columns
result_df = merged_df[["Application name", "File Type", "Timestamp_before", "Timestamp_after", "Emissions (gCO2eq)_before", "Emissions (gCO2eq)_after", "final emission", "Result"]]
result_df.columns = ["Application name", "File Type", "Timestamp (Before)", "Timestamp (After)", "Before", "After", "Final Emission", "Result"]

# Create 'Result' folder if it doesn't exist
if not os.path.exists(result_folder_path):
    os.makedirs(result_folder_path)

# Write to new CSV file
result_file_path = os.path.join(result_folder_path, "comparison_results.csv")
result_df.to_csv(result_file_path, index=False)

print(f"Comparison results saved to {result_file_path}")
