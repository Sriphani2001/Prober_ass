#!/usr/bin/python3
import sys
import time
import easysnmp
from easysnmp import Session

def parse_arguments():
    target_info = sys.argv[1]
    target_addr, target_port, target_community = target_info.split(":")
    sample_rate = float(sys.argv[2])
    total_samples = int(sys.argv[3])
    oids = sys.argv[4:]
    return target_addr, target_port, target_community, sample_rate, total_samples, oids

def initialize_session(target_addr, target_port, target_community):
    return Session(hostname=target_addr, remote_port=target_port, community=target_community, version=2, timeout=1, retries=1)

def handle_reset(curr_uptime, prev_uptime, iter_count):
    if curr_uptime < prev_uptime and iter_count != 0:
        print("Agent has RESET")
        return True
    return False

def process_responses(snmp_responses, prev_vals, curr_uptime, prev_uptime, iter_count, measure_time):
    curr_counter_vals, gauge_vals, octet_vals = [], [], []
    if iter_count != 0:
        print(f"{measure_time}|", end='')

    valid_data = [(resp.value, resp.snmp_type) 
                  for resp in snmp_responses[1:] 
                  if resp.value not in ['NOSUCHOBJECT', 'NOSUCHINSTANCE']]
    
    for val, data_type in valid_data:
        if data_type == 'GAUGE':
            gauge_vals.append(int(val))
        elif data_type in ['COUNTER', 'COUNTER64']:
            curr_counter_vals.append((int(val), data_type))
        elif data_type == 'OCTET_STR':
            octet_vals.append(val)
    
    if iter_count != 0:
        print_gauges(gauge_vals, prev_vals['gauge'])
        print_counters(curr_counter_vals, prev_vals['counter'], curr_uptime, prev_uptime)
        print_octets(octet_vals)
    
    prev_vals['counter'] = [val for val, _ in curr_counter_vals]
    prev_vals['gauge'] = gauge_vals
    prev_vals['uptime'] = curr_uptime
    
    if iter_count != 0:
        print()

def print_gauges(curr_gauges, prev_gauges):
    if prev_gauges:
        gauge_deltas = [(curr, curr - prev) for curr, prev in zip(curr_gauges, prev_gauges)]
        for curr, delta in gauge_deltas:
            print(f"{curr}({delta})|", end='')

def print_counters(curr_counters, prev_counters, curr_uptime, prev_uptime):
    if prev_counters:
        counter_deltas = [(curr, curr - prev, data_type) for (curr, data_type), prev in zip(curr_counters, prev_counters)]
        for curr, delta, data_type in counter_deltas:
            if delta < 0:
                delta += (2 ** 32) if data_type == 'COUNTER' else (2 ** 64)
            time_delta = float(curr_uptime - prev_uptime)
            rate = int(delta / time_delta)
            print(f"{rate}|", end='')

def print_octets(octet_vals):
    for val in octet_vals:
        print(f"{val}|", end='')

def main():
    target_addr, target_port, target_community, sample_rate, total_samples, oids = parse_arguments()
    time_step = 1 / sample_rate
    snmp_conn = initialize_session(target_addr, target_port, target_community)
    oids.insert(0, '1.3.6.1.2.1.1.3.0')
    
    prev_vals = {'counter': [], 'gauge': [], 'uptime': 0}
    
    if total_samples == -1:
        iter_count = 0
        while True:
            measure_time = int(time.time())
            try:
                snmp_responses = snmp_conn.get(oids)
                curr_uptime = int(snmp_responses[0].value) / 100
                if handle_reset(curr_uptime, prev_vals['uptime'], iter_count):
                    prev_vals = {'counter': [], 'gauge': [], 'uptime': curr_uptime}
                    continue
                process_responses(snmp_responses, prev_vals, curr_uptime, prev_vals['uptime'], iter_count, measure_time)
                iter_count += 1
                time.sleep(max(0, measure_time + time_step - time.time()))
            except easysnmp.exceptions.EasySNMPTimeoutError:
                print(f"{measure_time}| Timeout")
    else:
        for iter_count in range(total_samples + 1):
            measure_time = int(time.time())
            try:
                snmp_responses = snmp_conn.get(oids)
                curr_uptime = int(snmp_responses[0].value) / 100
                if handle_reset(curr_uptime, prev_vals['uptime'], iter_count):
                    prev_vals = {'counter': [], 'gauge': [], 'uptime': curr_uptime}
                    continue
                process_responses(snmp_responses, prev_vals, curr_uptime, prev_vals['uptime'], iter_count, measure_time)
                time.sleep(max(0, measure_time + time_step - time.time()))
            except easysnmp.exceptions.EasySNMPTimeoutError:
                print(f"{measure_time}| Timeout")

if __name__ == "__main__":
    main()
