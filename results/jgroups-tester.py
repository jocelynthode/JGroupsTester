#!/usr/bin/env python3.5
import argparse
import re
import statistics
from collections import namedtuple
from enum import Enum

Stats = namedtuple('Stats', ['state', 'start_at', 'end_at', 'duration', 'msg_sent', 'msg_received'])


class State(Enum):
    perfect = 1
    late = 2
    dead = 3


parser = argparse.ArgumentParser(description='Process JGroups logs')
parser.add_argument('files', metavar='FILE', nargs='+', type=str,
                    help='the files to parse')
parser.add_argument('-e', '--experiments-nb', metavar='EXPERIMENT_NB', type=int, default=1,
                    help='How many experiments were run')
args = parser.parse_args()
experiments_nb = args.experiments_nb


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
    file.seek(0)  # Start again

    # We want the last occurrence in the file
    def find_end():
        result = None
        pos = None
        events_sent = 0
        state = State.perfect
        for line in it:
            match = re.match(r'(\d+) - Delivered', line)
            if match:
                result = int(match.group(1))
                pos = file.tell()
            elif re.match(r'\d+ - Sending:', line):
                events_sent += 1
            elif re.match(r'\d+ - Time given was smaller than current time', line):
                state = State.late

        file.seek(pos)
        return textiter(file), result, events_sent, state

    it, end_at, evts_sent, state = find_end()
    messages_sent = match_line(r'\d+ - Events sent: (\d+)')
    if not messages_sent:
        return Stats(State.dead, start_at, end_at, end_at - start_at, evts_sent, None)
    messages_received = match_line(r'\d+ - Events received: (\d+)')

    return Stats(state, start_at, end_at, end_at - start_at, messages_sent, messages_received)


def all_stats():
    for file in args.files:
        with open(file, 'r') as f:
            file_stats = extract_stats(f)
        yield file_stats


def global_time(experiment_nb, stats):
    for i in range(experiment_nb):
        start_index = i * perfect_length
        end_index = start_index + perfect_length
        tmp = stats[start_index:end_index]
        mininum_start = min([stat.start_at for stat in tmp])
        maximum_end = max([stat.end_at for stat in tmp])
        yield (maximum_end - mininum_start)


stats = list(all_stats())
perfect_stats = [stat for stat in stats if stat.state == State.perfect]
late_stats = [stat for stat in stats if stat.state == State.late]
dead_stats = [stat for stat in stats if stat.state == State.dead]

stats_length = len(stats) / experiments_nb
perfect_length = len(perfect_stats) / experiments_nb
late_length = len(late_stats) / experiments_nb
dead_length = len(dead_stats) / experiments_nb

if not stats_length.is_integer() or not perfect_length.is_integer()\
        or not late_length.is_integer() or not dead_length.is_integer():
    raise ArithmeticError('Length should be an integer')

stats_length = int(stats_length)
perfect_length = int(perfect_length)
late_length = int(late_length)
dead_length = int(dead_length)

global_times = list(global_time(experiments_nb, perfect_stats))
durations = [stat.duration for stat in perfect_stats if stat.duration]
mininum = min(durations)
maximum = max(durations)
average = statistics.mean(durations)
global_average = statistics.mean(global_times)


print("JGroups run with initially %d peers across %d experiments" % (perfect_length + dead_length, experiments_nb))
print("Churn -> Peers created: {:d}, Peers killed {:d} in each experiment".format(late_length, dead_length))
print("-------------------------------------------")
print("Least time to deliver in total : %d ms" % mininum)
print("Most time to deliver in total : %d ms" % maximum)
print("Average time to deliver per peer in total: %d ms" % average)
print("Average global time to deliver on all peers per experiment: %d ms" % global_average)
print("-------------------------------------------")
messages_sent = [stat.msg_sent for stat in stats if stat.msg_sent]
messages_received = [stat.msg_received for stat in perfect_stats if stat.msg_received]

all_delivered = []
for i in range(experiments_nb):
    start_index_sent = i * stats_length
    end_index_sent = start_index_sent + stats_length
    start_index_received = i * perfect_length
    end_index_received = start_index_received + perfect_length
    events_sent = sum(messages_sent[start_index_sent:end_index_sent])
    events_received = sum(messages_received[start_index_received:end_index_received]) / perfect_length

    print("Experiment %d:" % (i + 1))
    print("Total events sent: %d" % events_sent)
    print("Total events received on average: %f" % events_received)
    print("Ratio events received/sent: {:.10g}".format(events_received / events_sent))
    print("-------------------------------------------")
    all_delivered.append(events_sent == events_received)
print("-------------------------------------------")


def check_list_all_identical(lst):
    return not lst or [lst[0]] * len(lst) == lst


if check_list_all_identical(all_delivered):
    print("All events sent were delivered in every experiments")
else:
    for idx, result in enumerate(all_delivered):
        if not result:
            print("Experiment %d didn't deliver every event sent" % idx)
