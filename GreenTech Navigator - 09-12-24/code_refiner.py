import os
import shutil
import logging
import time
import requests
import json
from pathlib import Path
from typing import List, Set
from dotenv import load_dotenv
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('code_refiner.log'),
        logging.StreamHandler()
    ]
)

class CodeRefiner:    
    def __init__(self):
        """Initialize the CodeRefiner with model from environment variables."""
        self.load_environment()
        self.setup_api()

    def parse_extensions(self, extensions_str: str) -> Set[str]:
        """Parse file extensions from string to set."""
        try:
            # Remove spaces and split by comma
            extensions = [ext.strip() for ext in extensions_str.split(',')]
            # Ensure all extensions start with a dot
            extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]
            return set(extensions)
        except Exception as e:
            logging.error(f"Error parsing file extensions: {str(e)}")
            raise

    def get_default_models(self) -> dict:
        """Return default models configuration."""
        return {
            "qwen-7b-chat": "Qwen/Qwen-7B-Chat",
            "qwen-14b-chat": "Qwen/Qwen-14B-Chat",
            "qwen-1.5b": "Qwen/Qwen-1_8B-Chat",
            "qwen-coder": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
            "qwen-32b": "Qwen/Qwen2.5-Coder-32B-Instruct"
        }
   
   
    def load_environment(self) -> None:
        """Load and validate environment variables."""
        try:
            BASE_DIR = '/app/project'
            env_path = '/app/.env'

            # Load environment variables
            # env_path = os.path.join(BASE_DIR, ".env")
            if os.path.exists(env_path):
                load_dotenv(dotenv_path=env_path, verbose=True, override=True)
            else:
                logging.warning(f"Environment file {env_path} not found. Using default values.")
            
            # Load basic configurations
            self.project_path = BASE_DIR
            self.prompt = os.getenv('PROMPT_1')
            # Add test case prompt
            self.test_prompt = os.getenv('PROMPT_GENERATE_TESTCASES', 
                'Create testcase functions for the given code. Provide only the code without any markdown, comments, or explanations.')
            self.hf_token = os.getenv('HF_TOKEN')

            # Test suite directory names
            self.src_test_suite = 'SRC-TestSuite'
            self.greencode_test_suite = 'GreenCode-TestSuite'
            
            # Load API URL
            self.api_base_url = os.getenv('API_URL', 'https://api-inference.huggingface.co/models/')
            
            # Load and parse file extensions
            extensions_str = os.getenv('QWEN_FILE_EXTENSIONS', '.py,.java,.cpp,.cs,.js,.ts')
            self.supported_extensions = self.parse_extensions(extensions_str)
            
            # Load excluded files
            self.excluded_files = os.getenv('EXCLUDED_FILES', '').split(',')
            self.excluded_files = [f.strip() for f in self.excluded_files if f.strip()]
            
            # Use default models configuration
            self.available_models = self.get_default_models()
            
            # Get selected model from environment
            self.model_key = os.getenv('AZURE_MODEL', '').lower()
            if not self.model_key or self.model_key not in self.available_models:
                available_models = list(self.available_models.keys())
                raise ValueError(f"Invalid or missing model selection in .env file. Choose from: {available_models}")
            
            # Validate required variables
            if not all([self.project_path, self.prompt, self.hf_token]):
                missing = []
                if not self.project_path: missing.append('PROJECT_PATH')
                if not self.prompt: missing.append('PROMPT_1')
                if not self.hf_token: missing.append('HF_TOKEN')
                raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
                
            self.project_path = Path(self.project_path)
            if not self.project_path.exists():
                raise ValueError(f"Project path does not exist: {self.project_path}")
                
            # Log configurations
            logging.info(f"Environment loaded successfully")
            logging.info(f"Selected model: {self.model_key}")
            logging.info(f"Project path: {self.project_path}")
            logging.info(f"Supported extensions: {self.supported_extensions}")
            logging.info(f"API URL: {self.api_base_url}")
            logging.info(f"Excluded files: {self.excluded_files}")
            
        except Exception as e:
            logging.error(f"Error loading environment: {str(e)}")
            raise
            
    def setup_api(self) -> None:
        """Setup the API connection."""
        try:
            self.model_url = self.api_base_url + self.available_models[self.model_key]
            self.headers = {"Authorization": f"Bearer {self.hf_token}"}
            logging.info(f"API setup completed for model: {self.available_models[self.model_key]}")
        except Exception as e:
            logging.error(f"Error setting up API: {str(e)}")
            raise

    def query_api(self, payload: dict) -> dict:
        """Send request to Hugging Face API."""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.model_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise Exception(f"API request failed after {max_retries} attempts: {str(e)}")
                logging.warning(f"API request attempt {attempt + 1} failed, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)

    def refine_code(self, code: str) -> str:
        """Refine code using the Hugging Face API."""
        try:
            # Prepare the prompt
            prompt = f"{self.prompt}\n\nCode:\n{code}\n\nRefined Code:"
            
            # Prepare the payload
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 2048,
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "do_sample": True
                }
            }
            
            # Query the API
            response = self.query_api(payload)
            
            # Extract the refined code
            if isinstance(response, list) and len(response) > 0:
                generated_text = response[0].get('generated_text', '')
                refined_code = generated_text.split("Refined Code:")[-1].strip()
                return refined_code
            else:
                raise ValueError("Unexpected API response format")
            
        except Exception as e:
            logging.error(f"Error refining code: {str(e)}")
            raise

    def process_file(self, file_path: Path) -> None:
        """Process a single code file."""
        try:
            # Skip excluded files
            if file_path.name in self.excluded_files:
                logging.info(f"Skipping excluded file: {file_path.name}")
                return
                
            # Read the original code
            with open(file_path, 'r', encoding='utf-8') as f:
                original_code = f.read()
                
            # Refine the code
            refined_code = self.refine_code(original_code)
            
            # Calculate relative path
            relative_path = file_path.relative_to(self.project_path)
            output_file = self.output_path / relative_path
            
            # Create necessary directories
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write refined code
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(refined_code)
                
            logging.info(f"Successfully processed: {relative_path}")
            
        except Exception as e:
            logging.error(f"Error processing file {file_path}: {str(e)}")
            raise

    def setup_output_directory(self) -> None:
        """Setup the GreenCode output directory."""
        try:
            self.output_path = self.project_path / 'GreenCode'
            
            if self.output_path.exists():
                logging.info("Removing existing GreenCode directory...")
                shutil.rmtree(self.output_path)
                
            self.output_path.mkdir(parents=True)
            logging.info(f"Created output directory: {self.output_path}")
            
        except Exception as e:
            logging.error(f"Error setting up output directory: {str(e)}")
            raise

    def get_code_files(self) -> List[Path]:
        """Recursively find all supported code files in the project."""
        try:
            code_files = []
            total_files = 0
            processed_files = 0
            skipped_files = 0
            
            # Log the start of file scanning
            logging.info("Starting to scan for code files...")
            logging.info(f"Looking for files with extensions: {self.supported_extensions}")
            
            for file_path in self.project_path.rglob('*'):
                total_files += 1
                
                # Skip directories and handle files only
                if not file_path.is_file():
                    continue
                    
                # Check if file is in SRC-TestSuite folder or other excluded conditions
                if (file_path.suffix in self.supported_extensions and 
                    'GreenCode' not in file_path.parts and
                    self.src_test_suite not in file_path.parts and  # Exclude SRC-TestSuite folder
                    file_path.name not in self.excluded_files):
                    code_files.append(file_path)
                    processed_files += 1
                else:
                    skipped_files += 1
            
            # Log detailed statistics
            logging.info(f"File scanning completed:")
            logging.info(f"Total files scanned: {total_files}")
            logging.info(f"Files to process: {processed_files}")
            logging.info(f"Files skipped: {skipped_files}")
            logging.info(f"Supported extensions found: {set(f.suffix for f in code_files)}")
            
            # Additional validation
            if not code_files:
                logging.warning("No matching code files found in the project directory!")
            
            return code_files
            
        except Exception as e:
            logging.error(f"Error finding code files: {str(e)}")
            raise

    def is_test_file(self, file_path: Path) -> bool:
        """Check if a file is a test file."""
        test_indicators = ['test', 'spec', 'Tests']
        file_stem = file_path.stem.lower()
        return any(indicator.lower() in file_stem for indicator in test_indicators)

    def get_test_file_path(self, source_file: Path, base_dir: Path, test_suite_dir: Path) -> Path:
        """Generate the path for the test file."""
        # Get relative path from base directory
        relative_path = source_file.relative_to(base_dir)
        
        # Create test file path
        test_file_name = f"{source_file.stem}Test{source_file.suffix}"
        test_file_path = test_suite_dir / relative_path.parent / test_file_name
        
        return test_file_path

    def existing_test_file(self, source_file: Path, test_suite_dir: Path) -> bool:
        """Check if a test file already exists in the test suite directory."""
        potential_test_names = [
            f"{source_file.stem}Test{source_file.suffix}",
            f"test_{source_file.stem}{source_file.suffix}",
            f"{source_file.stem}_test{source_file.suffix}",
            f"{source_file.stem}.test{source_file.suffix}"
        ]
        
        # Get relative path without filename
        relative_dir = source_file.parent.relative_to(self.project_path)
        test_dir = test_suite_dir / relative_dir
        
        # Check in the corresponding test suite directory
        for test_name in potential_test_names:
            if (test_dir / test_name).exists():
                return True
        
        return False


    def generate_test_case(self, code: str) -> str:
        """Generate test cases using the API."""
        try:
            # Prepare the prompt
            prompt = f"{self.test_prompt}\n\nCode:\n{code}"
            
            # Prepare the payload
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 2048,
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "do_sample": True
                }
            }
            
            # Query the API
            response = self.query_api(payload)
            
            # Extract the test code
            if isinstance(response, list) and len(response) > 0:
                generated_text = response[0].get('generated_text', '')
                test_code = generated_text.split("Code:")[-1].strip()
                return test_code
            else:
                raise ValueError("Unexpected API response format")
            
        except Exception as e:
            logging.error(f"Error generating test case: {str(e)}")
            raise

    def process_tests_for_directory(self, source_dir: Path, test_suite_dir: Path) -> None:
        """Process test cases for all files in a directory."""
        try:
            # Create test suite directory
            test_suite_dir.mkdir(parents=True, exist_ok=True)
            
            # Collect files that need test cases
            code_files = []
            for file_path in source_dir.rglob('*'):
                # Determine if we're processing GreenCode directory
                is_greencode = 'GreenCode' in source_dir.parts
                
                if (file_path.suffix in self.supported_extensions and 
                    not self.is_test_file(file_path) and 
                    not self.existing_test_file(file_path, test_suite_dir) and
                    (is_greencode or 'GreenCode' not in file_path.parts) and  # Modified condition
                    'TestSuite' not in file_path.parts and
                    file_path.name not in self.excluded_files):
                    code_files.append(file_path)
            
            logging.info(f"Found {len(code_files)} files requiring test cases in {source_dir}")
            
            # Add more detailed logging
            if not code_files:
                logging.warning(f"No files found matching criteria in {source_dir}. Check file extensions and exclusion rules.")
                for file_path in source_dir.rglob('*'):
                    if file_path.is_file():
                        logging.debug(f"Found file: {file_path}, Extension: {file_path.suffix}")
            
            for file_path in tqdm(code_files, desc=f"Generating tests for {source_dir.name}"):
                try:
                    # Read the source code
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    
                    # Generate test case
                    test_code = self.generate_test_case(source_code)
                    
                    # Get test file path
                    test_file_path = self.get_test_file_path(file_path, source_dir, test_suite_dir)
                    
                    # Create directory if it doesn't exist
                    test_file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write test file
                    with open(test_file_path, 'w', encoding='utf-8') as f:
                        f.write(test_code)
                    
                    logging.info(f"Generated test case for: {file_path.relative_to(source_dir)}")
                    
                except Exception as e:
                    logging.error(f"Error processing tests for {file_path}: {str(e)}")
                    continue
                    
        except Exception as e:
            logging.error(f"Error processing tests for directory {source_dir}: {str(e)}")
            raise

    def process_greencode_tests(self) -> None:
        """Process test cases for GreenCode directory."""
        try:
            # Create test suite directory inside GreenCode
            test_suite_dir = self.output_path / self.greencode_test_suite
            
            # Process only files in GreenCode directory
            self.process_tests_for_directory(self.output_path, test_suite_dir)
            
        except Exception as e:
            logging.error(f"Error processing GreenCode tests: {str(e)}")
            raise

    def process_source_tests(self) -> None:
        """Process test cases for source directory."""
        try:
            # Create test suite directory in project root
            test_suite_dir = self.project_path / self.src_test_suite
            
            # Process only files in source directory
            self.process_tests_for_directory(self.project_path, test_suite_dir)
            
        except Exception as e:
            logging.error(f"Error processing source tests: {str(e)}")
            raise


    def run(self) -> None:
        """Main execution method."""
        try:
            print(f"Starting code refinement and test generation process...")
            
            # First phase: Code refinement
            self.setup_output_directory()
            code_files = self.get_code_files()
            
            if not code_files:
                print("No files to process. Please check your QWEN_FILE_EXTENSIONS configuration.")
                return
                
            # Process code refinement
            for file_path in tqdm(code_files, desc="Processing files for optimization"):
                try:
                    print(f"\nOptimizing: {file_path.name}")
                    self.process_file(file_path)
                    time.sleep(0.1)
                except Exception as e:
                    logging.error(f"Skipping file {file_path} due to error: {str(e)}")
                    continue
            
            logging.info("Code refinement completed successfully")
            
            # Second phase: Test case generation
            print("\nStarting test case generation...")
            
            # Generate tests for root directory first
            print("\nGenerating tests for original source files...")
            self.process_source_tests()
            
            # Generate tests for GreenCode directory
            print("\nGenerating tests for optimized files...")
            self.process_greencode_tests()
            
            logging.info("Test case generation completed successfully")
            print("\nCode refinement and test generation process completed!")
            
        except Exception as e:
            logging.error(f"Error during execution: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        refiner = CodeRefiner()
        refiner.run()
    except Exception as e:
        logging.error(f"Application failed: {str(e)}")
