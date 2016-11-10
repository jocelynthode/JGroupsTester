#!/usr/bin/env python3
import argparse
import docker
import logging
import signal
import subprocess
import threading
import time

from churn import Churn
from churn import churn_tuple
from churn import get_peer_list
from datetime import datetime
from docker import errors
from docker import types
from docker import utils
from nodes_trace import NodesTrace


cli = docker.Client(base_url='unix://var/run/docker.sock')
MANAGER_IP = '172.16.2.119'
LOG_STORAGE = '/home/jocelyn/tmp/data'
LOCAL_DATA_FILES = '/home/jocelyn/tmp/data/*.txt'
REPOSITORY = 'swarm-m:5000/'
SERVICE_NAME = 'jgroups'
TRACKER_NAME = 'jgroups-tracker'


def create_service(service_name, image, env=None, mounts=None, placement=None, replicas=1):
    container_spec = types.ContainerSpec(image=image, env=env, mounts=mounts)
    logging.debug(container_spec)
    task_tmpl = types.TaskTemplate(container_spec,
                                   resources=types.Resources(mem_limit=314572800),
                                   restart_policy=types.RestartPolicy(),
                                   placement=placement)
    logging.debug(task_tmpl)
    cli.create_service(task_tmpl, name=service_name, mode={'Replicated': {'Replicas': replicas}})


def run_churn():
    if args.synthetic:
        logging.info(args.synthetic)
        nodes_trace = NodesTrace(synthetic=args.synthetic)
    else:
        nodes_trace = NodesTrace(database='database.db')

    if args.local:
        hosts_fname = None
    else:
        hosts_fname = 'hosts'

    delta = args.delta
    churn = Churn(hosts_filename=hosts_fname, kill_coordinator_round=args.kill_coordinator)

    # Add initial cluster
    logging.debug('Initial size: {}'.format(nodes_trace.initial_size()))
    churn.add_processes(nodes_trace.initial_size())
    nodes_trace.next()

    if args.delay:
        delay = (datetime.utcfromtimestamp(args.delay // 1000) - datetime.utcnow()).seconds
        if delay < 0:
            delay = 0
    else:
        delay = 0

    logging.info("Starting churn at {:s} UTC"
                 .format(datetime.utcfromtimestamp(args.delay // 1000).isoformat()))
    time.sleep(delay)
    logging.info("Starting churn")
    if args.local:
        churn.peer_list = get_peer_list(LOCAL_DATA_FILES)
    else:
        churn.peer_list = get_peer_list()

    logging.debug(churn.peer_list)
    churn.coordinator = churn.peer_list.pop(0)

    for _, to_kill, to_create in nodes_trace:
        logging.debug("curr_size: {:d}, to_kill: {:d}, to_create {:d}"
                      .format(_, len(to_kill), len(to_create)))
        churn.add_suspend_processes(len(to_kill), len(to_create))
        time.sleep(delta)

    logging.info("Churn finished")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run benchmarks',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('peer_number', type=int, help='With how many peer should it be ran')
    parser.add_argument('time_add', type=int, help='Delay experiments start in ms')
    parser.add_argument('events_to_send', type=int, help='How many events each peer should send')
    parser.add_argument('rate', type=int, help='At which frequency should a peer send an event in ms')
    parser.add_argument('-x', '--fixed-rate', type=int, default=None,
                        help='Fix the rate at which a peer will send events')
    parser.add_argument('-l', '--local', action='store_true',
                        help='Run locally')
    parser.add_argument('-n', '--runs', type=int, default=1, help='How many experiments should be ran')
    parser.add_argument('--verbose', '-v', action='store_true', help='Switch DEBUG logging on')

    subparsers = parser.add_subparsers(help='Specify churn and its arguments')

    churn_parser = subparsers.add_parser('churn', help='Activate churn')
    churn_parser.add_argument('delta', type=int, default=60,
                              help='The interval between killing/adding new containers in s')
    churn_parser.add_argument('--kill-coordinator', '-k', type=int, nargs='+',
                              help='Kill the coordinator at the specified periods')
    churn_parser.add_argument('--synthetic', '-s', metavar='N', type=churn_tuple, nargs='+',
                              help='Pass the synthetic list (to_kill,to_create)(example: 0,100 0,1 1,0)')
    churn_parser.add_argument('--delay', '-d', type=int,
                              help='At which time should the churn start (UTC)')

    args = parser.parse_args()

    if not args.fixed_rate:
        args.fixed_rate = args.peer_number
    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(format='%(levelname)s: %(asctime)s - %(message)s', level=log_level)
    logging.info("START")

    def signal_handler(signal, frame):
        print('Stopping Benchmarks')
        try:
            cli.remove_service(SERVICE_NAME)
            cli.remove_service(TRACKER_NAME)
            if not args.local:
                time.sleep(15)
                with subprocess.Popen(['while', 'read', 'ip;', 'do', 'rsync', '--remove-source-files',
                                       '-av', '"${ip}":~/data/"', '../data/', 'done', '<hosts'],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      universal_newlines=True) as p:
                    for line in p.stdout:
                        print(line)

        except errors.NotFound:
            pass
        exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    if args.local:
        service_image = SERVICE_NAME
        tracker_image = TRACKER_NAME
        with subprocess.Popen(['cd', '../;', './gradlew', 'docker'],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True) as p:
            for line in p.stdout:
                print(line)
    else:
        service_image = REPOSITORY + SERVICE_NAME
        tracker_image = REPOSITORY + TRACKER_NAME

    exit(0)

    if not args.local:
        for line in cli.pull(service_image, stream=True):
            print(line)
        for line in cli.pull(tracker_image, stream=True):
            print(line)
    else:
        pass
        # TODO build image

    try:
        cli.init_swarm()
        if not args.local:
            # TODO find TOKEN
            token = 0
            subprocess.call(['parallel-ssh', '-t', '0', '-h', 'hosts',
                            '"docker swarm join --token {:s} {:s}:2377"'.format(token, MANAGER_IP)])
        ipam_pool = utils.create_ipam_pool(subnet='172.111.0.0/16')
        ipam_config = utils.create_ipam_config(pool_configs=[ipam_pool])
        cli.create_network('jgroups_network', 'overlay', ipam=ipam_config)
    except errors.APIError:
        logging.info('Host is already part of a swarm')

    for run_nb, _ in enumerate(range(args.runs), 1):
        create_service(TRACKER_NAME, tracker_image, placement={'Constraints': ['node.role == manager']})
        # TODO wait for jgroups-tracker to be started
        time.sleep(10)
        environment_vars = {'PEER_NUMBER': args.peer_number, 'TIME': args.time_add,
                            'EVENTS_TO_SEND': args.events_to_send, 'RATE': args.rate,
                            'FIXED_RATE': args.fixed_rate}
        environment_vars = ['%s=%d' % (k, v) for k, v in environment_vars.items()]
        logging.debug(environment_vars)

        service_replicas = 0 if hasattr(args, 'churn') else args.peer_number
        create_service(SERVICE_NAME, service_image, env=environment_vars,
                       mounts=[types.Mount(target='/data', source=LOG_STORAGE)])
        logging.info('Running EpTO tester -> Experiment: %d' % run_nb)
        if hasattr(args, 'churn'):
            threading.Thread(target=run_churn, daemon=True).start()

        # TODO wait for JGroups benchmarks to be done

        cli.remove_service('jgroups-service')
        cli.remove_service('jgroups-tracker')

        logging.info("Services removed")
        time.sleep(30)

        if not args.local:
            subprocess.call(['parallel-ssh', '-t', '0', '-h', 'hosts',
                             '"mkdir -p data/test-$i/capture &&  mv data/*.txt data/test-{:d} '
                             '&& mv data/capture/*.csv data/test-{:d}/capture"'.format(run_nb, run_nb)])

            subprocess.call(['mkdir', '-p', '~/data/test-{:d}/capture'.format(run_nb)])
            subprocess.call(['mv', '~/data/*.txt', '~/data/test-{:d}'.format(run_nb)])
            subprocess.call(['mv', '~/data/capture/*.csv', '~/data/test-{:d}/capture'.format(run_nb)])

    logging.info("Benchmark done!")

