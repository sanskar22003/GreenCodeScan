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
    except KeyError as e
