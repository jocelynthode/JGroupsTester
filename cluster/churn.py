#!/usr/bin/env python3
import glob
import logging
import random
import re
import subprocess


def churn_tuple(s):
    try:
        _to_kill, _to_create = map(int, s.split(','))
        return _to_kill, _to_create
    except:
        raise TypeError("Tuples must be (int, int)")


def get_peer_list(path='../data/*.txt'):
    with open(glob.glob(path)[0], 'r') as f:
        a_list = []
        for line in f.readlines():
            match = re.match(r'\d+ - View: (.+)', line)
            if match:
                a_list = match.group(1).split(',')
                break
        if not a_list:
            raise LookupError('No view found in file {}'.format(f.name))
        return a_list


class Churn:
    """
    Author: Jocelyn Thode

    A class in charge of adding/suspending nodes to create churn in a JGroups SEQUENCER cluster
    """
    containers = {}
    coordinator = None
    peer_list = []
    periods = 0

    def __init__(self, hosts_filename=None, kill_coordinator_round=''):
        self.hosts = ['localhost']
        if hosts_filename is not None:
            with open(hosts_filename, 'r') as file:
                self.hosts += list(line.rstrip() for line in file)
        self.kill_coordinator_round = kill_coordinator_round
        self.cluster_size = 0

    def suspend_processes(self, to_suspend_nb):
        if to_suspend_nb < 0:
            raise ArithmeticError('Suspend number must be greater or equal to 0')
        if to_suspend_nb == 0:
            return
        for i in range(to_suspend_nb):
            command_suspend = ["docker", "kill", '--signal=SIGSTOP']
            if self.periods in self.kill_coordinator_round:
                command_suspend += [self.coordinator]
                logging.debug(command_suspend)
                subprocess.call(command_suspend)
                logging.info("Coordinator on host localhost was suspended")
                self.coordinator = self.peer_list.pop(0)
                return

            choice = random.choice(self.hosts)
            if choice not in self.containers:
                command_ps = ["docker", "ps", "-aqf", "name=jgroups-service", "-f", "status=running"]
                if choice != 'localhost':
                    command_ps = ["ssh", choice] + command_ps

                self.containers[choice] = subprocess.check_output(command_ps,
                                                                  universal_newlines=True).splitlines()

            if choice != 'localhost':
                command_suspend = ["ssh", choice] + command_suspend

            try:
                container = random.choice(self.containers[choice])
                logging.debug('container: {:s}, coordinator: {:s}'.format(container, self.coordinator))
                while container == self.coordinator:
                    container = random.choice(self.containers[choice])
                self.containers[choice].remove(container)
            except ValueError or IndexError:
                logging.error("No container available")
                return

            command_suspend += [container]
            subprocess.call(command_suspend)
            logging.info("Container {} on host {} was suspended"
                         .format(container, choice))

    def add_processes(self, to_create_nb):
        if to_create_nb < 0:
            raise ArithmeticError('Add number must be greater or equal to 0')
        if to_create_nb == 0:
            return
        self.cluster_size += to_create_nb
        subprocess.call(["docker", "service", "scale",
                         "jgroups-service={:d}".format(self.cluster_size)])

    def add_suspend_processes(self, to_suspend_nb, to_create_nb):
        self.suspend_processes(to_suspend_nb)
        self.add_processes(to_create_nb)
        self.periods += 1