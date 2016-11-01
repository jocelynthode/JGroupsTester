#!/usr/bin/env python3
import subprocess
import random
import re
import argparse
import sched
import time

parser = argparse.ArgumentParser(description='Create a synthetic churn',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('delta', type=int, default=60,
                    help='The interval between killing/adding new containers in s')
parser.add_argument('-a', '--add-new-containers', action='store_true',
                    help='Whether we should add new containers during the churn')
parser.add_argument('--local', action='store_true', help='Run the synthetic churn only on local node')
parser.add_argument('--kill-coordinator', type=int, default=-1, help='Kill the coordinator at the specified period')
args = parser.parse_args()
DELTA = args.delta
MAX_PERIOD = 10
periods = 0
scheduler = sched.scheduler(time.time, time.sleep)


def get_hosts():
    hosts = ['localhost']
    if not args.local:
        with open('hosts', 'r') as file:
           hosts = list(line.rstrip() for line in file)
    return hosts

hosts = get_hosts()
containers = {}
service_nb = re.search(r'(\d+)/(\d+)', subprocess.check_output(
    ["docker", "service", "ls", "-f", "name=jgroups-service"], universal_newlines=True))

try:
    total_nb = int(service_nb.group(2))
    current_nb = int(service_nb.group(1))
except AttributeError:
    print("Service isn't running")
    exit(1)

while current_nb != total_nb:
    service_nb = re.search(r'(\d+)/\d+', subprocess.check_output(
        ["docker", "service", "ls", "-f", "name=jgroups-service"], universal_newlines=True))
    current_nb = int(service_nb.group(1))
    time.sleep(1)

print("All containers are running")
print("Sleeping for 180 seconds")
time.sleep(180)


def suspend_process():
    global periods
    command_suspend = ["docker", "kill", '--signal=SIGSTOP']
    if periods == args.kill_coordinator:
        container = subprocess.check_output(["docker", "ps", "-aqf", "name=jgroups-coordinator", "-f",
                                             "status=running"], universal_newlines=True).splitlines()
        command_suspend += container
        subprocess.call(command_suspend)
        print("Coordinator was suspended")
        return True

    choice = random.choice(hosts)
    if choice not in containers:
        command_ps = ["docker", "ps", "-aqf", "name=jgroups-service", "-f", "status=running"]
        if choice != 'localhost':
            command_ps = ["ssh", choice] + command_ps

        containers[choice] = subprocess.check_output(command_ps, universal_newlines=True).splitlines()

    if choice != 'localhost':
        command_suspend = ["ssh", choice] + command_suspend

    try:
        container = random.choice(containers[choice])
        containers[choice].remove(container)
    except ValueError or IndexError:
        print("No container available")
        return False

    command_suspend += [container]
    subprocess.call(command_suspend)
    print("Container {} on host {} was suspended".format(container, choice))
    return True


def add_process():
    global total_nb
    total_nb += 1
    subprocess.call(["docker", "service", "scale", "jgroups-service={:d}".format(total_nb)])


def add_suspend_process():
    if suspend_process():
        add_process()

print("Starting churn")


def do_churn(action):
    global periods
    while periods < MAX_PERIOD:
        action()
        periods += 1
        time.sleep(DELTA)

if args.add_new_containers:
    do_churn(add_suspend_process)
else:
    do_churn(suspend_process)

print("Churn finished")
