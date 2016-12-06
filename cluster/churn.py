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


def get_peer_list(peer_number, path='../data/*.txt'):
    with open(glob.glob(path)[0], 'r') as f:
        a_list = []
        for line in f.readlines():
            match = re.match(r'\d+ - View: (.+)', line)
            if match:
                a_list = match.group(1).split(',')
                break
        if not a_list:
            raise LookupError('No view found in file {}'.format(f.name))
        if len(a_list) < peer_number:
            raise AssertionError('Peer List is smaller than expected')
        return a_list


class Churn:
    """
    Author: Jocelyn Thode

    A class in charge of adding/suspending nodes to create churn in a JGroups SEQUENCER cluster
    """

    def __init__(self, hosts_filename=None, kill_coordinator_round='', service_name='jgroups', repository=''):
        self.containers = {}
        self.coordinator = None
        self.peer_list = []
        self.periods = 0
        self.suspended_containers = []
        self.logger = logging.getLogger('churn')

        self.service_name = service_name
        self.repository = repository
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

        already_killed = False
        for i in range(to_suspend_nb):
            command_suspend = ["docker", "kill", '--signal=SIGSTOP']
            if not already_killed and self.periods in self.kill_coordinator_round:
                command_suspend += [self.coordinator]
                for host, containers in self.containers.items():
                    if self.coordinator in containers:
                        if host != 'localhost':
                            command_suspend = ["ssh", host] + command_suspend

                        count = 0
                        while count < 3:
                            try:
                                subprocess.check_call(command_suspend, stdout=subprocess.DEVNULL)
                                self.logger.info('Coordinator {:s} on host {:s} was suspended'.format(self.coordinator, host))
                                self.suspended_containers.append(self.coordinator)
                            except subprocess.CalledProcessError:
                                count += 1
                                self.logger.error("Container couldn't be removed, retrying...")
                                if count >= 3:
                                    self.logger.error("Container couldn't be removed", exc_info=True)
                                    raise
                                continue
                            break

                self.coordinator = self.peer_list.pop(0)
                already_killed = True
                continue

            # Retry until we find a working choice
            count = 0
            while count < 5:
                try:
                    choice = random.choice(self.hosts)
                    self._refresh_host_containers(choice)
                    container, command_suspend = self._choose_container(command_suspend, choice)
                    self.logger.debug('container: {:s}, coordinator: {:s}'.format(container, self.coordinator))
                    while container in self.suspended_containers or container == self.coordinator:
                        command_suspend = ["docker", "kill", '--signal=SIGSTOP']
                        choice = random.choice(self.hosts)
                        self._refresh_host_containers(choice)
                        container, command_suspend = self._choose_container(command_suspend, choice)
                except (ValueError, IndexError):
                    count += 1
                    if not self.containers[choice]:
                        self.hosts.remove(choice)
                    self.logger.error('Error when trying to pick a container')
                    if count == 5:
                        self.logger.error('Stopping churn because no container was found')
                        raise
                    continue
                break

            command_suspend.append(container)
            count = 0
            while count < 3:
                try:
                    subprocess.check_call(command_suspend, stdout=subprocess.DEVNULL)
                    self.logger.info('Container {} on host {} was suspended'
                                     .format(container, choice))
                    self.peer_list.remove(container)
                    self.suspended_containers.append(container)
                except subprocess.CalledProcessError:
                    count += 1
                    self.logger.error("Container couldn't be removed, retrying...")
                    if count >= 3:
                        self.logger.error("Container couldn't be removed", exc_info=True)
                        raise
                    continue
                except ValueError:
                    pass
                break

    def add_processes(self, to_create_nb):
        if to_create_nb < 0:
            raise ArithmeticError('Add number must be greater or equal to 0')
        if to_create_nb == 0:
            return
        self.cluster_size += to_create_nb
        i = 0
        while True:
            try:
                subprocess.check_call(["docker", "service", "scale",
                                       "{:s}={:d}".format(self.service_name, self.cluster_size)],
                                      stdout=subprocess.DEVNULL)
                break
            except subprocess.CalledProcessError:
                if i >= 5:
                    raise
                self.logger.error("Couldn't scale service")
                i += 1
                continue

        self.logger.info('Service scaled up to {:d}'.format(self.cluster_size))

    def add_suspend_processes(self, to_suspend_nb, to_create_nb):
        self.suspend_processes(to_suspend_nb)
        self.add_processes(to_create_nb)
        self.periods += 1

    def set_logger_level(self, log_level):
        self.logger.setLevel(log_level)

    def _choose_container(self, command_suspend, host):
        if host != 'localhost':
            command_suspend = ["ssh", host] + command_suspend

        container = random.choice(self.containers[host])
        self.containers[host].remove(container)
        return container, command_suspend

    def _refresh_host_containers(self, host):
        command_ps = ["docker", "ps", "-aqf",
                      "name={service},status=running,ancestor={repo}{service}".format(
                          service=self.service_name, repo=self.repository)]
        if host != 'localhost':
            command_ps = ["ssh", host] + command_ps

        self.containers[host] = subprocess.check_output(command_ps,
                                                        universal_newlines=True).splitlines()
