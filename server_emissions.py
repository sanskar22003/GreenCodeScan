import pandas as pd
import psutil
import socket
from datetime import datetime
import time
import os
from dotenv import load_dotenv
# Load environment variables
env_path = os.path.abspath(".env")
load_dotenv(dotenv_path=env_path, verbose=True, override=True)
# Directory and file path constants
BYTES_TO_GB = 1024 ** 3
MILLI_WATTS_TO_KILOWATTS = 1000
GLOBAL_GRID_CO2_FACTOR = 0.54
US_GRID_CO2_FACTOR = 0.46
GLOBAL_RENEWABLE_CO2_FACTOR = 0.01
DEFAULT_SLEEP_TIME = 20
RUN_TIME_IN_MINUTES = 1
RESULT_DIR = os.path.join(os.path.dirname(env_path), 'Result')
EXCEL_FILE = os.path.join(RESULT_DIR, 'server_data.xlsx')
def ensure_result_directory_exists():
    if not os.path.exists(RESULT_DIR):
        os.makedirs(RESULT_DIR)
def get_system_info():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent
    network_usage = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
    energy_consumption = get_energy_consumption(cpu_usage, ram_usage, disk_usage, network_usage)
    co2_emission = calculate_co2_emission(energy_consumption)
    return {
        'Date': datetime.now().strftime("%Y-%m-%d"),
        'Time': datetime.now().strftime("%H:%M:%S"),
        'Host-name': hostname,
        'IP address': ip_address,
        'CPU usage': cpu_usage,
        'RAM usage': ram_usage,
        'Disk usage': disk_usage,
        'Network usage': network_usage,
        'Energy consumption (KWH)': energy_consumption,
        'CO2 emission (kt)': co2_emission
    }
def get_max_power_consumption():
    cpu_max_freq = psutil.cpu_freq().max
    ram_size_gb = psutil.virtual_memory().total / BYTES_TO_GB
    disk_size_gb = sum(psutil.disk_usage(part.mountpoint).total for part in psutil.disk_partitions()) / BYTES_TO_GB
    max_power_consumption = calculate_power_consumption(cpu_max_freq, ram_size_gb, disk_size_gb)
    return max_power_consumption
def calculate_power_consumption(cpu_max_freq, ram_size_gb, disk_size_gb):
    CPU_FREQ_FACTOR = 1000
    RAM_SIZE_FACTOR = 16
    DISK_SIZE_FACTOR = 1000
    BASE_POWER_CONSUMPTION = 200
    LOAD_FACTOR = 1.0
    cpu_factor = cpu_max_freq / CPU_FREQ_FACTOR
    ram_factor = ram_size_gb / RAM_SIZE_FACTOR
    disk_factor = disk_size_gb / DISK_SIZE_FACTOR
    total_factor = cpu_factor + ram_factor + disk_factor + LOAD_FACTOR
    max_power_consumption = total_factor * BASE_POWER_CONSUMPTION
    return max_power_consumption
def get_energy_consumption(cpu_usage, ram_usage, disk_usage, network_usage):
    max_power_consumption = get_max_power_consumption()
    cpu_factor = cpu_usage / 100
    ram_factor = ram_usage / 100
    disk_factor = disk_usage / 100
    network_factor = network_usage / (BYTES_TO_GB / MILLI_WATTS_TO_KILOWATTS)
    total_factor = (cpu_factor + ram_factor + disk_factor + network_factor) / 4
    return total_factor * max_power_consumption / MILLI_WATTS_TO_KILOWATTS
def calculate_co2_emission(energy_consumption):
    co2_emission_factors = {
        'grid': {
            'global': GLOBAL_GRID_CO2_FACTOR,
            'us': US_GRID_CO2_FACTOR,
        },
        'renewable': {
            'global': GLOBAL_RENEWABLE_CO2_FACTOR,
        },
    }
    energy_source = 'grid'
    location = 'global'
    co2_emission_per_kwh = co2_emission_factors.get(energy_source, {}).get(location, GLOBAL_GRID_CO2_FACTOR)
    co2_emission = energy_consumption * co2_emission_per_kwh / MILLI_WATTS_TO_KILOWATTS
    return co2_emission
def update_excel(data_list):
    ensure_result_directory_exists()
    try:
        df = pd.read_excel(EXCEL_FILE)
    except FileNotFoundError:
        df = pd.DataFrame(columns=['Date', 'Time', 'Host-name', 'IP address', 'CPU usage', 'RAM usage', 'Disk usage', 'Network usage', 'Energy consumption (KWH)', 'CO2 emission (kt)'])
    
    # Convert the list of dictionaries into a DataFrame
    new_data = pd.DataFrame(data_list)
    
    # Ensure new_data is not empty before concatenation
    if not new_data.empty:
        df = pd.concat([df, new_data], ignore_index=True)
    
    # Save the updated DataFrame back to the Excel file
    df.to_excel(EXCEL_FILE, index=False)
def main():
    data_list = []
    start_time = time.time()
    while True:
        data = get_system_info()
        data_list.append(data)
        time.sleep(DEFAULT_SLEEP_TIME)
        if time.time() - start_time > RUN_TIME_IN_MINUTES * 60:
            break
    # Write all collected data to Excel at once
    update_excel(data_list)
if __name__ == "__main__":
    main()
