import os

# Directory containing the cloned files
cloned_files_directory = r"C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline"

# Directory to store the generated test files
test_files_directory = r"C:\ProgramData\Jenkins\.jenkins\workspace\GreenCodeScanPipeline\tests"

# Make sure the test files directory exists
os.makedirs(test_files_directory, exist_ok=True)

# Iterate over the files in the cloned files directory
for filename in os.listdir(cloned_files_directory):
    if filename.endswith(".py"):
        # Create a test file for this Python file
        test_filename = f"test_{filename}"
        test_filepath = os.path.join(test_files_directory, test_filename)

        with open(test_filepath, 'w') as test_file:
            # Write a basic test function that imports the Python file and checks if it runs without errors
            test_file.write(f"""
import pytest

def test_{filename.replace('.py', '')}():
    try:
        import {filename.replace('.py', '')}
    except Exception as e:
        pytest.fail(f"Execution failed with {str(e)}", pytrace=False)
""")
