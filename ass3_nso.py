#!/usr/bin/python3
import easysnmp
from easysnmp import Session
import sys, time, math

Agent_name = sys.argv[1]
agent_iput = Agent_name.split(':')
Agent_Ipadd = agent_iput[0]
Agent_Port = agent_iput[1]
Community_of_agent = agent_iput[2]
SampleFreq = float(sys.argv[2])
Counts_sample = int(sys.argv[3])
SamplingTime = 1 / SampleFreq
ObjIDs = []
ObjectIdentifier1 = []
ObjectIdentifier2 = []
timer = ""

for cha in range(4, len(sys.argv)):
    ObjIDs.append(sys.argv[cha])

ObjIDs.insert(0, '1.3.6.1.2.1.1.3.0')

session = Session(hostname=Agent_Ipadd, remote_port=Agent_Port,
                  community=Community_of_agent, version=2, timeout=1, retries=3)

def chadu():
    global ObjectIdentifier1, new_time, timer2
    oput = session.get(ObjIDs)
    TimerSys = int(oput[0].value) / 100
    ObjectIdentifier2 = []

    for t in range(0, len(oput)):
        print("oput value{}".format(oput[t].value))

    if int(TimerSys) > 2**32 or int(TimerSys) <= 0:
        print("The system just restarted.")

    for du in range(1, len(oput)):
        if oput[du].value != 'NOSUCHOBJECT' and oput[du].value != 'NOSUCHINSTANCE':
            if oput[du].snmp_type in ['COUNTER64', 'GAUGE', 'COUNTER']:
                ObjectIdentifier2.append(int(oput[du].value))
            else:
                ObjectIdentifier2.append(oput[du].value)

            if count != 0 and len(ObjectIdentifier1) > 0:
                if TimerSys > new_time:
                    if oput[du].snmp_type in ['COUNTER', 'COUNTER32', 'COUNTER64']:
                        OIDdiff = int(ObjectIdentifier2[du - 1]) - int(ObjectIdentifier1[du - 1])
                        diff_time = (TimerSys - new_time)
                        rate = OIDdiff / diff_time

                        if rate < 0:
                            if oput[du].snmp_type == 'COUNTER32':
                                OIDdiff = OIDdiff + (2**32)
                            elif oput[du].snmp_type == 'COUNTER64':
                                OIDdiff = OIDdiff + (2**64)
                            rate = OIDdiff / diff_time

                        try:
                            if timer == str(timer2):
                                print(round(rate), end="|")
                            else:
                                print(timer2, "|", round(rate), end="|")
                                timer = str(timer2)
                        except:
                            print(timer2, "|", round(rate), end="|")
                            timer = str(timer2)
                    elif oput[du].snmp_type == 'GAUGE':
                        OIDdiff = int(ObjectIdentifier2[du - 1]) - int(ObjectIdentifier1[du - 1])
                        OIDdiff = "+" + str(OIDdiff)
                        try:
                            if timer == str(timer2):
                                print(ObjectIdentifier2[len(ObjectIdentifier2) - 1], "(", +OIDdiff, ")", end="|")
                            else:
                                print(timer2, "|", ObjectIdentifier2[len(ObjectIdentifier2) - 1], "(", +OIDdiff, ")", end="|")
                                timer = str(timer2)
                        except:
                            print(timer2, "|", ObjectIdentifier2[len(ObjectIdentifier2) - 1], "(", +OIDdiff, ")", end="|")
                            timer = str(timer2)
            else:
                print("This seems like the system was restarted.")
                break

    ObjectIdentifier1 = ObjectIdentifier2
    new_time = TimerSys

if Counts_sample == -1:
    count = 0
    ObjectIdentifier1 = []
    while True:
        timer2 = time.time()
        chadu()
        if count != 0:
            print(end="\n")
        ResponseTime = time.time()
        count += 1
        if SamplingTime >= ResponseTime - timer2:
            time.sleep(SamplingTime - ResponseTime + timer2)
        else:
            n = math.ceil((ResponseTime - timer2) / SamplingTime)
            time.sleep((n * SamplingTime) - ResponseTime + timer2)
else:
    ObjectIdentifier1 = []
    for count in range(0, Counts_sample + 1):
        timer2 = time.time()
        chadu()
        if count != 0:
            print(end="\n")
        ResponseTime = time.time()
        if SamplingTime >= ResponseTime - timer2:
            time.sleep(SamplingTime - ResponseTime + timer2)
        else:
            n = math.ceil((ResponseTime - timer2) / SamplingTime)
            time.sleep((n * SamplingTime) - ResponseTime + timer2)
