import pandas as pd
import os

# Define file paths
emissions_path = "C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline\\Refined Files\\Result\\main_before_emissions_data.csv"
emissions_after_path = "C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline\\Refined Files\\Result\\main_after_emissions_data.csv"
result_folder_path = "C:\\ProgramData\\Jenkins\\.jenkins\\workspace\\GreenCodeScanPipeline\\Refined Files\\Result"

# Read CSV files
emissions_df = pd.read_csv(emissions_path)
emissions_after_df = pd.read_csv(emissions_after_path)

# Merge dataframes on common columns
merged_df = emissions_df.merge(emissions_after_df, on=["Customer Name", "Application name", "File Type"], suffixes=('_before', '_after'))

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
