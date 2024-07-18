import pandas as pd
import psutil
import socket
from datetime import datetime
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=".env", verbose=True, override=True)

# Define all paths and constants here
RESULT_DIR = os.getenv('RESULT_DIR')
EXCEL_FILE = os.path.join(RESULT_DIR, 'server_data.xlsx')
SLEEP_TIME = 20  # Sleep for 20 seconds before collecting data again
RUN_TIME = 60 * 2  # Run for 1 hour

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
    cpu_info = psutil.cpu_freq()
    cpu_max_freq = cpu_info.max
    ram_size_gb = psutil.virtual_memory().total / (1024 ** 3)
    disk_partitions = psutil.disk_partitions()
    disk_size_gb = sum(psutil.disk_usage(part.mountpoint).total for part in disk_partitions) / (1024 ** 3)
    max_power_consumption = calculate_power_consumption(cpu_max_freq, ram_size_gb, disk_size_gb)
    return max_power_consumption

def calculate_power_consumption(cpu_max_freq, ram_size_gb, disk_size_gb):
    cpu_factor = cpu_max_freq / 1000
    ram_factor = ram_size_gb / 16
    disk_factor = disk_size_gb / 1000
    load_factor = 1.0
    total_factor = cpu_factor + ram_factor + disk_factor + load_factor
    max_power_consumption = total_factor * 200
    return max_power_consumption

def get_energy_consumption(cpu_usage, ram_usage, disk_usage, network_usage):
    max_power_consumption = get_max_power_consumption()
    cpu_factor = cpu_usage / 100
    ram_factor = ram_usage / 100
    disk_factor = disk_usage / 100
    network_factor = network_usage / (1024 * 1024)
    total_factor = (cpu_factor + ram_factor + disk_factor + network_factor) / 4
    return total_factor * max_power_consumption / 1000

def calculate_co2_emission(energy_consumption):
    co2_emission_factors = {
        'grid': {
            'global': 0.54,
            'us': 0.46,
        },
        'renewable': {
            'global': 0.01,
        },
    }
    energy_source = 'grid'
    location = 'global'
    if energy_source in co2_emission_factors:
        if location in co2_emission_factors[energy_source]:
            co2_emission_per_kwh = co2_emission_factors[energy_source][location]
        else:
            co2_emission_per_kwh = co2_emission_factors[energy_source]['global']
    else:
        co2_emission_per_kwh = co2_emission_factors['grid']['global']
    co2_emission = energy_consumption * co2_emission_per_kwh / 1000
    return co2_emission

def update_excel(data):
    try:
        df = pd.read_excel(EXCEL_FILE)
    except FileNotFoundError:
        df = pd.DataFrame(columns=['Date', 'Time', 'Host-name', 'IP address', 'CPU usage', 'RAM usage', 'Disk usage', 'Network usage', 'Energy consumption (KWH)', 'CO2 emission (kt)'])
    df = pd.concat([df, pd.DataFrame(data, index=[0])], ignore_index=True)
    df.to_excel(EXCEL_FILE, index=False)

def main():
    start_time = time.time()
    while True:
        data = get_system_info()
        update_excel(data)
        time.sleep(SLEEP_TIME)
        if time.time() - start_time > RUN_TIME:
            break

if __name__ == "__main__":
    main()
