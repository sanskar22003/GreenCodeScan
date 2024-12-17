import os
import json
import subprocess
import csv
import time
import logging
import shutil
from datetime import datetime

import pandas as pd
from codecarbon import EmissionsTracker
from dotenv import load_dotenv

class EmissionsProcessor:
    def __init__(self, source_directory, green_refined_directory, result_dir):
        """
        Initialize the EmissionsProcessor with directory paths and configuration.
        
        :param source_directory: Base source directory for code processing
        :param green_refined_directory: Directory containing refined green code
        :param result_dir: Directory to store result files
        """
        # Load environment variables
        load_dotenv(verbose=True, override=True)
        
        self.SOURCE_DIRECTORY = source_directory
        self.GREEN_REFINED_DIRECTORY = green_refined_directory
        self.RESULT_DIR = result_dir
        
        # Load exclusion lists
        self.EXCLUDED_FILES = [file.strip() for file in os.getenv('EXCLUDED_FILES', '').split(',') if file.strip()]
        self.EXCLUDED_DIRECTORIES = [file.strip() for file in os.getenv('EXCLUDED_DIRECTORIES', '').split(',') if file.strip()]
    
    def get_test_command_generators(self):
        """
        Return a dictionary of test command generators for different languages.
        
        :return: Dictionary of test command generation functions
        """
        return {
            '.py': self.get_python_test_command,
            '.java': self.get_java_test_command,
            '.cpp': self.get_cpp_test_command,
            '.cs': self.get_cs_test_command
        }
    
    def process_emissions_for_file(self, tracker, script_path, emissions_csv, file_type, result_dir, test_command):
        """
        Process emissions and test results for a specific file.
        
        :param tracker: EmissionsTracker instance
        :param script_path: Path to the script file
        :param emissions_csv: Path to the emissions CSV file
        :param file_type: File extension type
        :param result_dir: Directory to store results
        :param test_command: Command to run tests for the file
        """
        if not test_command:
            return
        
        emissions_data = None
        duration = 0
        test_output = 'Unknown'
        script_name = os.path.basename(script_path)
        solution_dir = os.path.basename(os.path.dirname(script_path))
        is_green_refined = os.path.commonpath([script_path, self.GREEN_REFINED_DIRECTORY]) == self.GREEN_REFINED_DIRECTORY
        
        tracker_started = False
        try:
            tracker.start()
            tracker_started = True
            
            start_time = time.time()
            try:
                test_result = subprocess.run(test_command, capture_output=True, text=True, timeout=20)
                duration = time.time() - start_time
                test_output = 'Pass' if test_result.returncode == 0 else 'Fail'
            except subprocess.TimeoutExpired:
                test_output = 'Timeout'
        
        except Exception as e:
            logging.error(f"An error occurred while processing {script_name}: {e}")
            test_output = 'Error'
        
        finally:
            try:
                if tracker_started:
                    emissions_data = tracker.stop()
            except Exception as e:
                logging.error(f"Error stopping the tracker for {script_name}: {e}")
        
        self._record_emissions_data(
            emissions_data, 
            script_path, 
            file_type, 
            duration, 
            emissions_csv, 
            result_dir, 
            test_output, 
            solution_dir, 
            is_green_refined
        )
    
    def _record_emissions_data(self, emissions_data, script_path, file_type, duration, 
                                emissions_csv, result_dir, test_output, solution_dir, is_green_refined):
        """
        Record emissions data to CSV file.
        
        :param emissions_data: Emissions tracking data
        :param script_path: Path to the script file
        :param file_type: File extension type
        :param duration: Test execution duration
        :param emissions_csv: Path to the emissions CSV file
        :param result_dir: Directory to store results
        :param test_output: Test execution result
        :param solution_dir: Solution directory
        :param is_green_refined: Flag indicating if the file is in green refined directory
        """
        if emissions_data is not None:
            emissions_csv_default_path = 'emissions.csv'
            emissions_csv_target_path = os.path.join(result_dir, 'emissions.csv')
            try:
                if os.path.exists(emissions_csv_default_path):
                    shutil.move(emissions_csv_default_path, emissions_csv_target_path)
                
                if os.stat(emissions_csv_target_path).st_size != 0:
                    emissions_data_df = pd.read_csv(emissions_csv_target_path).iloc[-1]
                    data = [
                        os.path.basename(script_path),
                        file_type,
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        f"{emissions_data_df['emissions'] * 1000:.6f}",
                        f"{duration:.2f}",
                        f"{emissions_data_df['emissions_rate'] * 1000:.6f}",
                        f"{emissions_data_df['cpu_power']:.6f}",
                        f"{emissions_data_df['gpu_power']:.6f}",
                        f"{emissions_data_df['ram_power']:.6f}",
                        f"{emissions_data_df['cpu_energy'] * 1000:.6f}",
                        f"{emissions_data_df['gpu_energy']:.6f}",
                        f"{emissions_data_df['ram_energy'] * 1000:.6f}",
                        f"{emissions_data_df['energy_consumed'] * 1000:.6f}",
                        test_output,
                        solution_dir,
                        is_green_refined
                    ]
                    with open(emissions_csv, 'a', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerow(data)
                        file.flush()
                else:
                    logging.error(f"No emissions data found for {script_path}")
            except Exception as e:
                logging.error(f"Error processing emissions data for {script_path}: {e}")
        else:
            logging.error(f"Emissions data collection failed for {os.path.basename(script_path)}")
    
    def process_files_by_type(self, base_dir, emissions_data_csv, result_dir, file_extension, 
                               excluded_files, excluded_dirs, tracker, test_command_generator):
        """
        Process files of a specific type for emissions tracking.
        
        :param base_dir: Base directory to search for files
        :param emissions_data_csv: Path to the emissions CSV file
        :param result_dir: Directory to store results
        :param file_extension: File extension to process
        :param excluded_files: List of files to exclude
        :param excluded_dirs: List of directories to exclude
        :param tracker: EmissionsTracker instance
        :param test_command_generator: Function to generate test commands
        """
        files = []
        for root, dirs, file_list in os.walk(base_dir):
            # Exclude specified directories
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            
            # Additional directory filtering
            if base_dir == self.SOURCE_DIRECTORY:
                file_list = [f for f in file_list if self.GREEN_REFINED_DIRECTORY not in root]
            elif base_dir == self.GREEN_REFINED_DIRECTORY:
                file_list = [f for f in file_list if self.GREEN_REFINED_DIRECTORY in root]
            
            for script in file_list:
                if script.endswith(file_extension) and script not in excluded_files:
                    script_path = os.path.join(root, script)
                    test_command = test_command_generator(script_path)
                    if test_command:
                        files.append((script_path, test_command))
        
        # Process test files
        for script_path, test_command in files:
            self.process_emissions_for_file(
                tracker=tracker,
                script_path=script_path,
                emissions_csv=emissions_data_csv,
                file_type=file_extension,
                result_dir=result_dir,
                test_command=test_command
            )
    
    def get_python_test_command(self, script_path):
        """Generate test command for Python files."""
        return [os.getenv('PYTEST_PATH'), script_path] if 'test' in script_path.lower() else None
    
    def get_java_test_command(self, script_path):
        """Generate test command for Java files."""
        return [os.getenv('MAVEN_PATH'), '-Dtest=' + os.path.splitext(os.path.basename(script_path))[0] + 'Test', 'test'] if 'test' in script_path.lower() else None
    
    def get_cpp_test_command(self, script_path):
        """Generate test command for C++ files."""
        if 'test' in script_path.lower():
            test_file_name = os.path.basename(script_path).replace('.cpp', '_test.cpp')
            test_dir = os.path.join(os.path.dirname(script_path), 'test')
            test_file_path = os.path.join(test_dir, test_file_name)
            
            if not os.path.exists(test_file_path):
                logging.info(f"Warning: Test file {test_file_path} does not exist")
                return None
            
            build_dir = os.path.join(test_dir, 'build')
            os.makedirs(build_dir, exist_ok=True)
            
            cmake_config_command = [
                os.getenv('GTEST_CMAKE_PATH', 'cmake'), 
                f'-S{test_dir}', 
                f'-B{build_dir}', 
                '-DCMAKE_PREFIX_PATH=/usr/local',
                '-G', 'Unix Makefiles'
            ]
            
            cmake_build_command = [
                os.getenv('GTEST_CMAKE_PATH', 'cmake'), 
                '--build', 
                build_dir
            ]
            
            test_executable = os.path.join(build_dir, f'{os.path.splitext(test_file_name)[0]}')
            run_test_command = [test_executable]
            
            return cmake_config_command + cmake_build_command + run_test_command
        
        return None
    
    def get_cs_test_command(self, script_path):
        """Generate test command for C# files."""
        return [os.getenv('NUNIT_PATH'), 'test', os.path.splitext(os.path.basename(script_path))[0] + '.dll'] if 'test' in script_path.lower() else None
    
    def process_folder(self, base_dir, emissions_data_csv, result_dir, suffix, excluded_dirs):
        """
        Process a folder for emissions tracking across different programming languages.
        
        :param base_dir: Base directory to process
        :param emissions_data_csv: Path to the emissions CSV file
        :param result_dir: Directory to store results
        :param suffix: Suffix for logging
        :param excluded_dirs: List of directories to exclude
        """
        # Ensure result directory exists
        if not os.path.exists(result_dir):
            os.makedirs(result_dir)
            logging.info(f"Directory '{result_dir}' created successfully!")
        
        # Create CSV if not exists
        if not os.path.exists(emissions_data_csv):
            with open(emissions_data_csv, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "Application name", "File Type", "Timestamp", "Emissions (gCO2eq)",
                    "Duration", "emissions_rate", "CPU Power (KWh)", "GPU Power (KWh)", "RAM Power (KWh)",
                    "CPU Energy (Wh)", "GPU Energy (KWh)", "RAM Energy (Wh)", "Energy Consumed (Wh)", 
                    "Test Results", "solution dir", "Is Green Refined"
                ])
        
        # Initialize tracker
        tracker = EmissionsTracker()
        
        # Test command generators
        test_cmd_generators = self.get_test_command_generators()
        
        # Process files for each language
        for ext, test_cmd_generator in test_cmd_generators.items():
            self.process_files_by_type(
                base_dir=base_dir,
                emissions_data_csv=emissions_data_csv,
                result_dir=result_dir,
                file_extension=ext,
                excluded_files=self.EXCLUDED_FILES,
                excluded_dirs=excluded_dirs,
                tracker=tracker,
                test_command_generator=test_cmd_generator
            )
        
        logging.info(f"Emissions data and test results written to {emissions_data_csv}")
