#!/usr/bin/env python3.5
import re
from collections import namedtuple
import statistics
import argparse

Stats = namedtuple('Stats', ['start_at', 'end_at', 'duration', 'msg_sent', 'msg_received'])

parser = argparse.ArgumentParser(description='Process JGroups logs')
parser.add_argument('files', metavar='FILE', nargs='+', type=str,
                    help='the files to parse')
parser.add_argument('-e', '--experiments-nb',  metavar='EXPERIMENT_NB', type=int, default=1,
                    help='How many experiments were run')
args = parser.parse_args()
experiments_nb = args.experiments_nb
PEER_NUMBER = len(args.files) // experiments_nb


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
        with open(file, 'r') as f:
            file_stats = extract_stats(f)
        yield file_stats


def global_time(experiment_nb, stats):
    for i in range(experiment_nb):
        start_index = i * PEER_NUMBER
        end_index = start_index + PEER_NUMBER
        tmp = stats[start_index:end_index]
        mininum_start = min([stat.start_at for stat in tmp])
        maximum_end = max([stat.end_at for stat in tmp])
        yield(maximum_end - mininum_start)


stats = list(all_stats())
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
print("Average global time to deliver on all peers per experiment: %d ms" % global_average)

messages_sent = [stat.msg_sent for stat in stats]
messages_received = [stat.msg_received for stat in stats]

sent_sum = sum(messages_sent)
received_sum = sum(messages_received)
print("Total events sent: %d" % sent_sum)
print("Total events received on average: %f" % (received_sum / PEER_NUMBER))
print("-------------------------------------------")


def all_delivered(experiment_nb, stats):
    for i in range(experiment_nb):
        start_index = i * PEER_NUMBER
        end_index = start_index + PEER_NUMBER
        tmp = stats[start_index:end_index]
        total_received = tmp[0].msg_received
        sent_sum = sum([stat.msg_sent for stat in tmp])
        yield (sent_sum == total_received)

all_delivered = list(all_delivered(experiments_nb, stats))


def check_list_all_identical(lst):
    return not lst or [lst[0]]*len(lst) == lst

if check_list_all_identical(all_delivered):
    print("All events sent were delivered in every experiments")
else:
    for idx, result in enumerate(all_delivered):
        if not result:
            print("Experiment %d didn't deliver every event sent")

