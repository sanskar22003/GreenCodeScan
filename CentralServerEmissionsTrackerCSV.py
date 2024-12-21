import os
import json
import dotenv
import uuid
import time
import logging
import pandas as pd
import psutil
import socket
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import requests

# Load environment variables
env_path = os.path.abspath(".env")
load_dotenv(dotenv_path=env_path, verbose=True, override=True)

# Setup Logging
LOG_FILE = os.path.join(os.path.dirname(env_path), 'server_emissions.log')
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()

# Constants
BYTES_TO_GB = 1024 ** 3
MILLI_WATTS_TO_KILOWATTS = 1000
DEFAULT_SLEEP_TIME = int(os.getenv('DEFAULT_SLEEP_TIME', 20))
RUN_TIME_IN_MINUTES = int(os.getenv('RUN_TIME_IN_MINUTES', 1))
RESULT_DIR = os.path.join(os.path.dirname(env_path), 'Result')
CSV_FILE = os.path.join(RESULT_DIR, 'server_data.csv')

# Load CO2 emission factors from .env with defaults
GLOBAL_GRID_CO2_FACTOR = float(os.getenv('GLOBAL_GRID_CO2_FACTOR', 0.54))
US_GRID_CO2_FACTOR = float(os.getenv('US_GRID_CO2_FACTOR', 0.46))
GLOBAL_RENEWABLE_CO2_FACTOR = float(os.getenv('GLOBAL_RENEWABLE_CO2_FACTOR', 0.01))

# Server configuration
CENTRAL_SERVER_PORT = int(os.getenv('CENTRAL_SERVER_PORT', 5000))
SERVER_MODE = os.getenv('SERVER_MODE', 'agent')
CENTRAL_SERVER_URL = os.getenv('CENTRAL_SERVER_URL', 'http://localhost:5000')
SERVER_ID = os.getenv('SERVER_ID', str(uuid.uuid4()))

app = Flask(__name__)

# Store connected servers information
connected_servers = {}

def ensure_result_directory_exists():
    """Ensure that the Result directory exists."""
    try:
        if not os.path.exists(RESULT_DIR):
            os.makedirs(RESULT_DIR)
            logger.info(f"Directory '{RESULT_DIR}' created successfully!")
        else:
            logger.info(f"Directory '{RESULT_DIR}' already exists.")
    except Exception as e:
        logger.error(f"Failed to create directory '{RESULT_DIR}': {e}")
        raise

def get_max_power_consumption():
    """Calculate the maximum power consumption based on system specs."""
    try:
        cpu_max_freq = psutil.cpu_freq().max  # in MHz
        ram_size_gb = psutil.virtual_memory().total / BYTES_TO_GB  # in GB
        disk_size_gb = sum(psutil.disk_usage(part.mountpoint).total for part in psutil.disk_partitions()) / BYTES_TO_GB  # in GB
        max_power_consumption = calculate_power_consumption(cpu_max_freq, ram_size_gb, disk_size_gb)
        return max_power_consumption
    except Exception as e:
        logger.error(f"Error calculating max power consumption: {e}")
        raise

def calculate_power_consumption(cpu_max_freq, ram_size_gb, disk_size_gb):
    """Calculate power consumption based on hardware specifications."""
    try:
        CPU_FREQ_FACTOR = 1000
        RAM_SIZE_FACTOR = 16
        DISK_SIZE_FACTOR = 1000
        BASE_POWER_CONSUMPTION = 200  # in watts
        LOAD_FACTOR = 1.0

        cpu_factor = cpu_max_freq / CPU_FREQ_FACTOR
        ram_factor = ram_size_gb / RAM_SIZE_FACTOR
        disk_factor = disk_size_gb / DISK_SIZE_FACTOR

        total_factor = cpu_factor + ram_factor + disk_factor + LOAD_FACTOR
        max_power_consumption = total_factor * BASE_POWER_CONSUMPTION
        return max_power_consumption
    except Exception as e:
        logger.error(f"Error calculating power consumption: {e}")
        raise

def get_energy_consumption(cpu_usage, ram_usage, disk_usage, network_usage):
    """Calculate energy consumption based on system usage metrics."""
    try:
        max_power_consumption = get_max_power_consumption()

        cpu_factor = cpu_usage / 100
        ram_factor = ram_usage / 100
        disk_factor = disk_usage / 100
        network_factor = network_usage / (BYTES_TO_GB / MILLI_WATTS_TO_KILOWATTS)

        total_factor = (cpu_factor + ram_factor + disk_factor + network_factor) / 4
        energy_consumption = (total_factor * max_power_consumption) / MILLI_WATTS_TO_KILOWATTS

        return energy_consumption
    except Exception as e:
        logger.error(f"Error calculating energy consumption: {e}")
        raise

def calculate_co2_emission(energy_consumption):
    """Calculate CO2 emissions based on energy consumption."""
    try:
        co2_emission_factors = {
            'grid': {
                'global': GLOBAL_GRID_CO2_FACTOR,
                'us': US_GRID_CO2_FACTOR,
            },
            'renewable': {
                'global': GLOBAL_RENEWABLE_CO2_FACTOR,
            },
        }
        energy_source = os.getenv('ENERGY_SOURCE', 'grid')
        location = os.getenv('LOCATION', 'global')

        co2_emission_per_kwh = co2_emission_factors.get(energy_source, {}).get(location, GLOBAL_GRID_CO2_FACTOR)
        co2_emission = (energy_consumption * co2_emission_per_kwh) / MILLI_WATTS_TO_KILOWATTS

        return co2_emission
    except Exception as e:
        logger.error(f"Error calculating CO2 emission: {e}")
        raise

def get_system_info(previous_network):
    """Gather system information and calculate metrics."""
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        cpu_usage = psutil.cpu_percent(interval=1)
        ram_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent

        current_network = psutil.net_io_counters()
        bytes_sent = current_network.bytes_sent
        bytes_recv = current_network.bytes_recv
        network_delta = (bytes_sent - previous_network[0], bytes_recv - previous_network[1])
        total_network_usage = network_delta[0] + network_delta[1]

        energy_consumption = get_energy_consumption(cpu_usage, ram_usage, disk_usage, total_network_usage)
        co2_emission = calculate_co2_emission(energy_consumption)

        system_info = {
            'Date': datetime.now().strftime("%Y-%m-%d"),
            'Time': datetime.now().strftime("%H:%M:%S"),
            'Host-name': hostname,
            'IP address': ip_address,
            'CPU usage (%)': cpu_usage,
            'RAM usage (%)': ram_usage,
            'Disk usage (%)': disk_usage,
            'Network usage (bytes)': total_network_usage,
            'Energy consumption (KWH)': round(energy_consumption, 4),
            'CO2 emission (kt)': round(co2_emission, 4)
        }

        return system_info, (bytes_sent, bytes_recv)

    except Exception as e:
        logger.error(f"Error gathering system info: {e}")
        raise

def update_csv(system_info):
    """Update the CSV file with new system information."""
    try:
        ensure_result_directory_exists()
        
        # Add server_id to the data if it exists
        if 'server_id' not in system_info and SERVER_ID:
            system_info['server_id'] = SERVER_ID
            
        # If CSV doesn't exist, create it with headers
        if not os.path.exists(CSV_FILE):
            df = pd.DataFrame(columns=system_info.keys())
            df.to_csv(CSV_FILE, index=False)
            logger.info(f"CSV file '{CSV_FILE}' created with headers.")

        # Append the new data
        df_new = pd.DataFrame([system_info])
        df_new.to_csv(CSV_FILE, mode='a', header=False, index=False)
        logger.info(f"Appended new data to '{CSV_FILE}'.")
        
    except Exception as e:
        logger.error(f"Error updating CSV file '{CSV_FILE}': {e}")
        raise

class ServerEmissionsAgent:
    def __init__(self):
        self.previous_network = (0, 0)
        ensure_result_directory_exists()

    def collect_and_send_data(self):
        start_time = time.time()
        run_duration = RUN_TIME_IN_MINUTES * 60  # Convert to seconds
        
        while time.time() - start_time < run_duration:
            try:
                system_info, self.previous_network = get_system_info(self.previous_network)
                system_info['server_id'] = SERVER_ID
                
                # Send data to central server
                response = requests.post(
                    f"{CENTRAL_SERVER_URL}/report",
                    json=system_info
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully sent data to central server")
                else:
                    logger.error(f"Failed to send data to central server: {response.text}")
                
                time.sleep(DEFAULT_SLEEP_TIME)
                
            except Exception as e:
                logger.error(f"Error in agent data collection: {e}")
                time.sleep(DEFAULT_SLEEP_TIME)
        
        logger.info("Data collection completed for the specified duration")

class ServerEmissionsCentral:
    def __init__(self):
        ensure_result_directory_exists()

    def store_server_data(self, data):
        try:
            update_csv(data)
            logger.info(f"Stored data from server {data.get('server_id', 'unknown')}")
        except Exception as e:
            logger.error(f"Error storing server data: {e}")
            raise

# Flask routes for central server
@app.route('/report', methods=['POST'])
def report():
    try:
        data = request.get_json()
        server_emissions_central.store_server_data(data)
        connected_servers[data['server_id']] = {
            'last_seen': datetime.now().isoformat(),
            'hostname': data['Host-name'],
            'ip_address': data['IP address']
        }
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error processing report: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/servers', methods=['GET'])
def get_servers():
    return jsonify(connected_servers)

def main():
    """Main function to run either central server or agent."""
    try:
        if SERVER_MODE == 'central':
            global server_emissions_central
            server_emissions_central = ServerEmissionsCentral()
            logger.info("Starting central server...")
            app.run(host='0.0.0.0', port=CENTRAL_SERVER_PORT)
        else:
            logger.info("Starting agent server...")
            agent = ServerEmissionsAgent()
            agent.collect_and_send_data()
    except Exception as e:
        logger.error(f"An error occurred in the main function: {e}")
        raise

if __name__ == "__main__":
    main()