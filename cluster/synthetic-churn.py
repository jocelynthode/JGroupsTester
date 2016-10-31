#!/usr/bin/env python3.5
import subprocess
import random
import re
import argparse
import sched
import time

parser = argparse.ArgumentParser(description='Create a synthetic churn',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('delta', type=int, default=60000,
                    help='The interval between killing/adding new containers in ms')
parser.add_argument('-a', '--add-new-containers', type=bool, default=False,
                    help='Whether we should add new containers during the churn')
args = parser.parse_args()
DELTA = args.delta
scheduler = sched.scheduler(time.time, time.sleep)


def get_hosts():
    with open('hosts', 'r') as file:
       hosts = list(line.rstrip() for line in file)
    hosts.append('localhost')
    return hosts

hosts = get_hosts()
containers = {}
service_nb = re.search(r'(\d+)/(\d+)', subprocess.check_output(["docker", "service", "ls", "-f", "name=jgroups-service"]))
total_nb = int(service_nb.group(2))
current_nb = int(service_nb.group(1))

while current_nb != total_nb:
    service_nb = re.search(r'(\d+)/\d+', subprocess.check_output(["docker", "service", "ls", "-f", "name=jgroups-service"]))
    current_nb = int(service_nb.group(1))
    time.sleep(5)

print("All containers are running")
print("Sleeping for 180 seconds")
time.sleep(180)


def suspend_process():
    choice = random.choice(hosts)
    command_suspend = ["docker", "kill", '--signal="SIGTSTP']
    if not containers[choice]:
        command_ps = ["docker", "ps", "-aqf", "name=jgroups", "-f", "status=running"]
        if choice != 'localhost':
            command_ps = ["ssh", choice] + command_ps

        containers[choice] = subprocess.check_output(command_ps, universal_newlines=True).splitlines()

    if choice != 'localhost':
        command_suspend = ["ssh", choice] + command_suspend

    container = random.choice(containers[choice])
    try:
        containers[choice].remove(container)
    except ValueError:
        print("No container available")
        return False

    command_suspend += [container]
    subprocess.run(command_suspend)
    print("Container {} on host {} was suspended".format(container, choice))
    return True


def add_process():
    global total_nb
    total_nb += 1
    subprocess.run(["docker", "service", "scale", "jgroups-service={:d}".format(total_nb)])


def add_suspend_process():
    if suspend_process():
        add_process()


# From http://stackoverflow.com/a/2399145/2826574
def periodic(scheduler, interval, action, periods, actionargs=(), initial_delay=0):
    if initial_delay > 0:
        time.sleep(initial_delay)
    periods -= 1
    if periods <= 0:
        print("Churn finished")
        exit(0)
    scheduler.enter(interval, 1, periodic, (scheduler, interval, action, periods, actionargs))
    action(*actionargs)


print("Starting churn")
if args.add_new_containers:
    periodic(scheduler, DELTA, add_suspend_process, 10)
else:
    periodic(scheduler, DELTA, suspend_process, 10)
