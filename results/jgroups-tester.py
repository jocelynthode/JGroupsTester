#!/usr/bin/env python3.5
import re
from pathlib import Path
from collections import namedtuple
import statistics
import argparse

Stats = namedtuple('Stats', ['start_at', 'end_at', 'duration', 'msg_sent', 'msg_received'])

parser = argparse.ArgumentParser(description='Process JGroups logs')
parser.add_argument('peer_number', metavar='PEER_NUMBER', type=int,
                    help='the number of peer for an experiment')
parser.add_argument('files', metavar='FILE', nargs='+', type=argparse.FileType('r'),
                    help='the files to parse')
args = parser.parse_args()
PEER_NUMBER = args.peer_number


# We must create our own iter because iter disables the tell function
def textiter(file):
    line = file.readline()
    while line:
        yield line
        line = file.readline()


def extract_stats(file):
    it = textiter(file)  # Force re-use of same iterator

    def match_line(regexp_str):
        result = 0
        for line in it:
            match = re.match(regexp_str, line)
            if match:
                result = int(match.group(1))
                break
        return result

    start_at = match_line(r'(\d+) - Sending:')

    # We want the last occurrence in the file
    def find_end():
        result = None
        pos = None
        for line in it:
            match = re.match(r'(\d+) - Delivered', line)
            if match:
                result = int(match.group(1))
                pos = file.tell()

        file.seek(pos)
        return textiter(file), result

    it, end_at = find_end()
    messages_sent = match_line(r'\d+ - Events sent: (\d+)')
    messages_received = match_line(r'\d+ - Events received: (\d+)')

    return Stats(start_at, end_at, end_at - start_at, messages_sent, messages_received)


def all_stats():
    for file in args.files:
        yield extract_stats(file)


def global_time(experiment_nb, stats):
    for i in range(experiment_nb):
        start_index = i * PEER_NUMBER
        end_index = start_index + PEER_NUMBER
        tmp = stats[start_index:end_index]
        mininum_start = min([stat.start_at for stat in tmp])
        maximum_end = max([stat.end_at for stat in tmp])
        yield(maximum_end - mininum_start)


stats = list(all_stats())
experiments_nb = len(stats) // PEER_NUMBER

global_times = list(global_time(experiments_nb, stats))
durations = [stat.duration for stat in stats]
mininum = min(durations)
maximum = max(durations)
average = statistics.mean(durations)
global_average = statistics.mean(global_times)

print("JGroups run with %d peers across %d experiments" % (PEER_NUMBER, experiments_nb))
print("------------------------")
print("Least time to deliver in total : %d ms" % mininum)
print("Most time to deliver in total : %d ms" % maximum)
print("Average time to deliver per peer in total: %d ms" % average)

messages_sent = [stat.msg_sent for stat in stats]
messages_received = [stat.msg_received for stat in stats]

sent_sum = sum(messages_sent)
received_sum = sum(messages_received)
print("Total events sent: %d" % sent_sum)
print("Total events received on a single peer: %d" % messages_received[0])
print("Total events received across all peers: %d" % received_sum)

def all_delivered(experiment_nb, stats):
    for i in range(experiment_nb):
        start_index = i * PEER_NUMBER
        end_index = start_index + PEER_NUMBER
        tmp = stats[start_index:end_index]
        total_received = tmp[0].msg_received
        yield (sent_sum == total_received)

all_delivered = list(all_delivered(experiments_nb, stats))
def check_list_all_identical(lst):
    return not lst or [lst[0]]*len(lst) == lst

if check_list_all_identical(all_delivered):
    print("All events sent were delivered in every experiments")
else:
    for idx,result in enumerate(all_delivered):
        if not result:
            print("Experiement %d didn't deliver every event sent")


print("------------")
print("Average global time to deliver on all peers per experiment: %d ms" % global_average)
