import os
import logging
import pandas as pd
from dotenv import load_dotenv

from TrackerFunction import EmissionsProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
env_path = os.path.abspath(".env")
load_dotenv(dotenv_path=env_path, verbose=True, override=True)

# Define directories
SOURCE_DIRECTORY = os.path.dirname(env_path)
GREEN_REFINED_DIRECTORY = os.path.join(SOURCE_DIRECTORY, 'GreenCode')
RESULT_DIR = os.path.join(SOURCE_DIRECTORY, 'Result')
REPORT_DIR = os.path.join(SOURCE_DIRECTORY, 'Report')

def compare_emissions():
    """
    Compare emissions data from before and after green code refinement.
    """
    # Define paths to the before and after CSV files
    result_source_dir = os.path.join(RESULT_DIR, 'main_before_emissions_data.csv')
    result_green_refined_dir = os.path.join(RESULT_DIR, 'main_after_emissions_data.csv')

    # Check if both CSV files exist
    if not os.path.isfile(result_source_dir):
        logging.info(f"Source emissions data file not found: {result_source_dir}")
        return
    if not os.path.isfile(result_green_refined_dir):
        logging.info(f"Refined emissions data file not found: {result_green_refined_dir}")
        return

    # Read CSV files
    emissions_df = pd.read_csv(result_source_dir)
    emissions_after_df = pd.read_csv(result_green_refined_dir)

    # Merge dataframes on common columns
    try:
        merged_df = emissions_df.merge(
            emissions_after_df,
            on=["Application name", "File Type"],
            suffixes=('_before', '_after')
        )
    except KeyError as e:
        logging.info(f"Merge failed due to missing columns: {e}")
            return

    # Calculate the difference in emissions and determine the result
    merged_df['final emission'] = merged_df['Emissions (gCO2eq)_before'] - merged_df['Emissions (gCO2eq)_after']
    merged_df['Result'] = merged_df['final emission'].apply(lambda x: 'Improved' if x > 0 else 'Need improvement')

    # Select and rename columns
    result_df = merged_df[[
        "Application name",
        "File Type",
        "Timestamp_before",
        "Timestamp_after",
        "Emissions (gCO2eq)_before",
        "Emissions (gCO2eq)_after",
        "final emission",
        "Result"
    ]]
    result_df.columns = [
        "Application name",
        "File Type",
        "Timestamp (Before)",
        "Timestamp (After)",
        "Before",
        "After",
        "Final Emission",
        "Result"
    ]

    # Create 'Result' folder if it doesn't exist
    if not os.path.exists(RESULT_DIR):
        os.makedirs(RESULT_DIR)
        logging.info(f"Directory '{RESULT_DIR}' created successfully!")
    else:
        logging.info(f"Directory '{RESULT_DIR}' already exists.")

    # Write to new CSV file
    result_file_path = os.path.join(RESULT_DIR, "comparison_results.csv")
    result_df.to_csv(result_file_path, index=False)

    logging.info(f"Comparison results saved to {result_file_path}")

def prepare_detailed_data(result_dir):
    """
    Prepare detailed emissions data for analysis.
    
    :param result_dir: Directory containing result files
    :return: Tuple of solution directories and detailed data
    """
    comparison_csv = os.path.join(result_dir, "comparison_results.csv")
    before_csv = os.path.join(result_dir, 'main_before_emissions_data.csv')
    after_csv = os.path.join(result_dir, 'main_after_emissions_data.csv')
    
    # Read CSV files
    comparison_df = pd.read_csv(comparison_csv)
    before_df = pd.read_csv(before_csv)
    after_df = pd.read_csv(after_csv)
    
    # Merge before and after data
    merged_before = before_df[['Application name', 'File Type', 'Duration', 'Emissions (gCO2eq)', 'Energy Consumed (Wh)', 'solution dir']]
    merged_after = after_df[['Application name', 'File Type', 'Duration', 'Emissions (gCO2eq)', 'Energy Consumed (Wh)', 'solution dir']]
    
    # Get unique solution directories
    solution_dirs = sorted(set(before_df['solution dir']).union(after_df['solution dir']))
    
    # Prepare data for each solution dir
    detailed_data = {}
    for dir in solution_dirs:
        before_details = merged_before[merged_before['solution dir'] == dir].to_dict(orient='records')
        after_details = merged_after[merged_after['solution dir'] == dir].to_dict(orient='records')
        detailed_data[dir] = {
            'before': before_details,
            'after': after_details
        }
    
    return solution_dirs, detailed_data

def main():
    """
    Main function to orchestrate emissions tracking and comparison.
    """
    # Initialize EmissionsProcessor
    processor = EmissionsProcessor(
        source_directory=SOURCE_DIRECTORY,
        green_refined_directory=GREEN_REFINED_DIRECTORY,
        result_dir=RESULT_DIR
    )

    # Process original directory
    processor.process_folder(
        base_dir=SOURCE_DIRECTORY,
        emissions_data_csv=os.path.join(RESULT_DIR, 'main_before_emissions_data.csv'),
        result_dir=RESULT_DIR,
        suffix='before-in-detail',
        excluded_dirs=processor.EXCLUDED_DIRECTORIES
    )

    # Process green refined directory
    processor.process_folder(
        base_dir=GREEN_REFINED_DIRECTORY,
        emissions_data_csv=os.path.join(RESULT_DIR, 'main_after_emissions_data.csv'),
        result_dir=RESULT_DIR,
        suffix='after-in-detail',
        excluded_dirs=processor.EXCLUDED_DIRECTORIES
    )

    # Compare emissions
    compare_emissions()

    # Prepare detailed data
    solution_dirs, detailed_data = prepare_detailed_data(RESULT_DIR)
    
    logging.info("Emissions tracking and comparison completed successfully.")
    logging.info(f"Solution Directories: {solution_dirs}")

if __name__ == "__main__":
    main()
