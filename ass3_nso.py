#!/usr/bin/env python3
import easysnmp
from easysnmp import Session
import sys, time, math

# Extract agent details and command-line arguments
agent_info = sys.argv[1]
agent_details = agent_info.split(':')
agent_ip = agent_details[0]
agent_port = agent_details[1]
agent_community = agent_details[2]
sampling_frequency = float(sys.argv[2])
sample_count = int(sys.argv[3])
sampling_interval = 1 / sampling_frequency
oids = []

# Collect OIDs from command-line arguments
for i in range(4, len(sys.argv)):
    oids.append(sys.argv[i])

# Add sysUpTime OID to the list of OIDs to be monitored
oids.insert(0, '1.3.6.1.2.1.1.3.0')

# Initialize SNMP session
session = Session(hostname=agent_ip, remote_port=agent_port,
                  community=agent_community, version=2, timeout=1, retries=3)

# Function to fetch SNMP data and calculate rates
def fetch_snmp_data():
    global previous_values, previous_time, last_printed_time
    response = session.get(oids)
    current_time = int(response[0].value) / 100
    current_values = []

    # Print current OID values for debugging
    #for item in response:
    #   print(f"SNMP Response value: {item.value}")

    # Check if the system has restarted
    if int(current_time) > 2**32 or int(current_time) <= 0:
        print("The system just restarted.")

    # Process OID values from the response
    for i in range(1, len(response)):
        if response[i].value != 'NOSUCHOBJECT' and response[i].value != 'NOSUCHINSTANCE':
            if response[i].snmp_type in ['COUNTER64', 'GAUGE', 'COUNTER']:
                current_values.append(int(response[i].value))
            else:
                current_values.append(response[i].value)

            if count != 0 and len(previous_values) > 0:
                if current_time > previous_time:
                    if response[i].snmp_type in ['COUNTER', 'COUNTER32', 'COUNTER64']:
                        oid_difference = int(current_values[i - 1]) - int(previous_values[i - 1])
                        time_difference = (current_time - previous_time)
                        rate = oid_difference / time_difference

                        # Handle counter wrap-around
                        if rate < 0:
                            if response[i].snmp_type == 'COUNTER32':
                                oid_difference = oid_difference + (2**32)
                            elif response[i].snmp_type == 'COUNTER64':
                                oid_difference = oid_difference + (2**64)
                            rate = oid_difference / time_difference

                        try:
                            if last_printed_time == str(timer2):
                                print(round(rate), end="|")
                            else:
                                print(timer2, "|", round(rate), end="|")
                                last_printed_time = str(timer2)
                        except:
                            print(timer2, "|", round(rate), end="|")
                            last_printed_time = str(timer2)
                    elif response[i].snmp_type == 'GAUGE':
                        oid_difference = int(current_values[i - 1]) - int(previous_values[i - 1])
                        oid_difference = "+" + str(oid_difference)
                        try:
                            if last_printed_time == str(timer2):
                                print(current_values[-1], "(", oid_difference, ")", end="|")
                            else:
                                print(timer2, "|", current_values[-1], "(", oid_difference, ")", end="|")
                                last_printed_time = str(timer2)
                        except:
                            print(timer2, "|", current_values[-1], "(", oid_difference, ")", end="|")
                            last_printed_time = str(timer2)
            else:
                print("This seems like the system was restarted.")
                break

    previous_values = current_values
    previous_time = current_time

# Initialize variables for the main loop
previous_values = []
previous_time = None
last_printed_time = ""

# Infinite sampling loop if sample_count is -1
if sample_count == -1:
    count = 0
    while True:
        timer2 = time.time()
        fetch_snmp_data()
        if count != 0:
            print()
        response_time = time.time()
        count += 1
        if sampling_interval >= response_time - timer2:
            time.sleep(sampling_interval - response_time + timer2)
        else:
            n = math.ceil((response_time - timer2) / sampling_interval)
            time.sleep((n * sampling_interval) - response_time + timer2)
else:
    # Sampling loop for a specified number of samples
    for count in range(0, sample_count + 1):
        timer2 = time.time()
        fetch_snmp_data()
        if count != 0:
            print()
        response_time = time.time()
        if sampling_interval >= response_time - timer2:
            time.sleep(sampling_interval - response_time + timer2)
        else:
            n = math.ceil((response_time - timer2) / sampling_interval)
            time.sleep((n * sampling_interval) - response_time + timer2)
