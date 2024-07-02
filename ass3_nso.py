#!/usr/bin/python3
import sys
import time
from easysnmp import Session

# Extract command line arguments
target_info = sys.argv[1]
target_addr, target_port, target_community = target_info.split(":")
sample_rate = float(sys.argv[2])
total_samples = int(sys.argv[3])
time_step = 1 / sample_rate

# List of object identifiers (OIDs)
object_identifiers = []
prev_counter_vals = []
prev_gauge_vals = []
prev_octet_str_vals = []
snmp_responses = []
prev_uptime = 0

# Populate object identifiers from command line arguments
for idx in range(4, len(sys.argv)):
    object_identifiers.append(sys.argv[idx])

# Add sysUpTime OID to the beginning of the list
object_identifiers.insert(0, '1.3.6.1.2.1.1.3.0')

# Create SNMP session
snmp_conn = Session(hostname=target_addr, remote_port=target_port, community=target_community, version=2, timeout=1, retries=1)

def process_responses(iter_count, measure_time):
    global prev_counter_vals, prev_gauge_vals, prev_octet_str_vals, prev_uptime

    curr_counter_vals = []
    curr_gauge_vals = []
    curr_octet_str_vals = []

    # Print timestamp for each sample after the first one
    if iter_count != 0:
        print(f"{int(measure_time)} |", end='')

    # Extract valid responses
    valid_data = [(resp.value, resp.snmp_type) 
                  for resp in snmp_responses[1:] 
                  if resp.value not in ['NOSUCHOBJECT', 'NOSUCHINSTANCE']]
    
    # Separate values by type
    curr_gauge_vals = [int(val) for val, data_type in valid_data if data_type == 'GAUGE']
    curr_counter_vals = [(int(val), data_type) for val, data_type in valid_data if data_type in ['COUNTER', 'COUNTER64']]
    curr_octet_str_vals = [val for val, data_type in valid_data if data_type == 'OCTET_STR']

    # Print gauge values and their deltas
    if iter_count != 0 and prev_gauge_vals:
        gauge_deltas = [(curr, curr - prev) for curr, prev in zip(curr_gauge_vals, prev_gauge_vals)]
        for curr, delta in gauge_deltas:
            print(f"{curr}({delta}) |", end='')

    # Print counter rates
    if iter_count != 0 and prev_counter_vals:
        counter_deltas = [(curr, curr - prev, data_type) for (curr, data_type), prev in zip(curr_counter_vals, prev_counter_vals)]
        for curr, delta, data_type in counter_deltas:
            # Handle counter wrap-around
            if delta < 0:
                delta += (2 ** 32) if data_type == 'COUNTER' else (2 ** 64)
            time_delta = float(curr_uptime - prev_uptime)
            rate = int(delta / time_delta)
            print(f"{rate} |", end='')

    # Print octet string values
    if iter_count != 0 and prev_octet_str_vals:
        for curr, prev in zip(curr_octet_str_vals, prev_octet_str_vals):
            print(f"{curr} |", end='')

    # Update previous values for the next iteration
    prev_counter_vals = [val for val, _ in curr_counter_vals]
    prev_gauge_vals = curr_gauge_vals
    prev_octet_str_vals = curr_octet_str_vals
    prev_uptime = curr_uptime

    if iter_count != 0:
        print()

# Continuous sampling if total_samples is -1
if total_samples == -1:
    iter_count = 0
    while True:
        measure_time = time.time()
        snmp_responses = snmp_conn.get(object_identifiers)
        curr_uptime = int(snmp_responses[0].value) / 100
        detect_reset = lambda: curr_uptime < prev_uptime and iter_count != 0
        
        # Handle agent reset
        if detect_reset():
            print("Agent has RESET")
            prev_uptime = curr_uptime
            prev_counter_vals = []
            prev_gauge_vals = []
            prev_octet_str_vals = []
            continue
        
        process_responses(iter_count, measure_time)
        end_time = time.time()
        iter_count += 1

        # Sleep until the next sample time
        delay_until = lambda target_time: time.time() < target_time
        while delay_until(measure_time + time_step):
            pass

        # Adjust sleep time if processing took longer than time_step
        if end_time - measure_time > time_step:
            mult = 1
            adjusted_step = lambda m: m * time_step
            while end_time - measure_time > adjusted_step(mult):
                mult += 1
            while delay_until(measure_time + adjusted_step(mult)):
                pass
else:
    # Finite sampling loop
    for iter_count in range(total_samples + 1):
        measure_time = time.time()
        snmp_responses = snmp_conn.get(object_identifiers)
        curr_uptime = int(snmp_responses[0].value) / 100
        detect_reset = lambda: curr_uptime < prev_uptime and iter_count != 0
        
        # Handle agent reset
        if detect_reset():
            print("Agent has RESET")
            prev_uptime = curr_uptime
            prev_counter_vals = []
            prev_gauge_vals = []
            prev_octet_str_vals = []
            continue
        
        process_responses(iter_count, measure_time)
        end_time = time.time()

        # Sleep until the next sample time
        delay_until = lambda target_time: time.time() < target_time
        while delay_until(measure_time + time_step):
            pass

        # Adjust sleep time if processing took longer than time_step
        if end_time - measure_time > time_step:
            mult = 1
            adjusted_step = lambda m: m * time_step
            while end_time - measure_time > adjusted_step(mult):
                mult += 1
            while delay_until(measure_time + adjusted_step(mult)):
                pass
