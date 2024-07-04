#!/usr/bin/python3
import sys
import time
import easysnmp
from easysnmp import Session

def parse_arguments():
    # Parse command line arguments: target info, sample rate, total samples, and OIDs
    targetinfo = sys.argv[1]
    targetaddress, target_port, target_community = targetinfo.split(":")
    sample_rate = float(sys.argv[2])
    total_samples = int(sys.argv[3])
    oids = sys.argv[4:]
    return targetaddress, target_port, target_community, sample_rate, total_samples, oids

def initialize_session(targetaddress, target_port, target_community):
    # Initialize the SNMP session
    return Session(hostname=targetaddress, remote_port=target_port, community=target_community, version=2, timeout=1, retries=1)

def handle_reset(current_uptime, previous_uptime, iteration_count):
    # Check if the agent has reset based on the uptime values
    if current_uptime < previous_uptime and iteration_count != 0:
        print("Agent has RESET")
        return True
    return False

def process_responses(snmp_responses, previous_values, current_uptime, previous_uptime, iteration_count, measurement_time):
    current_counter_values, gauge_values, octet_values = [], [], []
    if iteration_count != 0:
        print(f"{measurement_time}|", end='')

    # Filter out invalid SNMP responses
    validdata = [(response.value, response.snmp_type) 
                  for response in snmp_responses[1:] 
                  if response.value not in ['NOSUCHOBJECT', 'NOSUCHINSTANCE']]
    
    # Categorize the SNMP response values
    for value, data_type in validdata:
        if data_type == 'GAUGE':
            gauge_values.append(int(value))
        elif data_type in ['COUNTER', 'COUNTER64']:
            current_counter_values.append((int(value), data_type))
        elif data_type == 'OCTET_STR':
            octet_values.append(value)
    
    # Print and compute the differences for the current iteration
    if iteration_count != 0:
        print_gauges(gauge_values, previous_values['gauge'])
        print_counters(current_counter_values, previous_values['counter'], current_uptime, previous_uptime)
        print_octets(octet_values)
    
    # Update previous values
    previous_values['counter'] = [value for value, _ in current_counter_values]
    previous_values['gauge'] = gauge_values
    previous_values['uptime'] = current_uptime
    
    if iteration_count != 0:
        print()

def print_gauges(current_gauges, previous_gauges):
    # Calculate and print gauge deltas
    if previous_gauges:
        gauge_deltas = [(current, current - previous) for current, previous in zip(current_gauges, previous_gauges)]
        for current, delta in gauge_deltas:
            print(f"{current}({delta})|", end='')

def print_counters(current_counters, previous_counters, current_uptime, previous_uptime):
    # Calculate and print counter deltas and rates
    if previous_counters:
        counter_deltas = [(current, current - previous, data_type) for (current, data_type), previous in zip(current_counters, previous_counters)]
        for current, delta, data_type in counter_deltas:
            if delta < 0:
                delta += (2 ** 32) if data_type == 'COUNTER' else (2 ** 64)
            time_delta = float(current_uptime - previous_uptime)
            rate = int(delta / time_delta)
            print(f"{rate}|", end='')

def print_octets(octet_values):
    # Print octet string values
    for value in octet_values:
        print(f"{value}|", end='')

def main():
    # Main function to initialize SNMP session and process responses
    targetaddress, target_port, target_community, sample_rate, total_samples, oids = parse_arguments()
    time_step = 1 / sample_rate
    snmp_connection = initialize_session(targetaddress, target_port, target_community)
    oids.insert(0, '1.3.6.1.2.1.1.3.0')  # Adding the system uptime OID
    
    previous_values = {'counter': [], 'gauge': [], 'uptime': 0}
    
    if total_samples == -1:
        iteration_count = 0
        while True:
            start_time = time.perf_counter()
            measurement_time = int(time.time())
            try:
                snmp_responses = snmp_connection.get(oids)
                current_uptime = int(snmp_responses[0].value) / 100
                if handle_reset(current_uptime, previous_values['uptime'], iteration_count):
                    previous_values = {'counter': [], 'gauge': [], 'uptime': current_uptime}
                    continue
                process_responses(snmp_responses, previous_values, current_uptime, previous_values['uptime'], iteration_count, measurement_time)
                iteration_count += 1
            except easysnmp.exceptions.EasySNMPTimeoutError:
                print(f"{measurement_time}| Timeout")
            
            end_time = time.perf_counter()
            elapsed_time = end_time - start_time
            sleep_time = max(0, time_step - elapsed_time)
            time.sleep(sleep_time)
    else:
        for iteration_count in range(total_samples + 1):
            start_time = time.perf_counter()
            measurement_time = int(time.time())
            try:
                snmp_responses = snmp_connection.get(oids)
                current_uptime = int(snmp_responses[0].value) / 100
                if handle_reset(current_uptime, previous_values['uptime'], iteration_count):
                    previous_values = {'counter': [], 'gauge': [], 'uptime': current_uptime}
                    continue
                process_responses(snmp_responses, previous_values, current_uptime, previous_values['uptime'], iteration_count, measurement_time)
            except easysnmp.exceptions.EasySNMPTimeoutError:
                print(f"{measurement_time}| Timeout")
            
            end_time = time.perf_counter()
            elapsed_time = end_time - start_time
            sleep_time = max(0, time_step - elapsed_time)
            time.sleep(sleep_time)

if __name__ == "__main__":
    main()
