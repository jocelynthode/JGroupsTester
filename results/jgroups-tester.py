#!/usr/bin/env python3.5
import argparse
import csv
import multiprocessing
import re
import statistics
from collections import namedtuple
from enum import Enum

import numpy as np
import progressbar

Stats = namedtuple('Stats', ['state', 'start_at', 'end_at', 'duration', 'msg_sent', 'msg_received'])


class State(Enum):
    perfect = 1
    late = 2
    dead = 3


parser = argparse.ArgumentParser(description='Process JGroups logs')
parser.add_argument('files', metavar='FILE', nargs='+', type=str,
                    help='the files to parse (must be given by experiments)')
parser.add_argument('-e', '--experiments-nb', metavar='EXPERIMENT_NB', type=int, default=1,
                    help='How many experiments were run')
args = parser.parse_args()
experiments_nb = args.experiments_nb
local_deltas = []
events_delivered = {}
events_sent_time = {}


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
    events_sent = {}
    events_delivered = {}
    local_deltas = []

    # We want the last occurrence in the file
    def find_end():
        result = None
        pos = None
        events_sent_count = 0
        state = State.perfect
        for line in it:
            match = re.match(r'(\d+) - Delivered: (.+)', line)
            if match:
                time = int(match.group(1))
                event = match.group(2)
                events_delivered[event] = time
                # Compute local deltas
                if event in events_sent:
                    local_deltas.append(events_delivered[event] - events_sent[event])
                result = int(match.group(1))
                pos = file.tell()
                continue
            match = re.match(r'(\d+) - Sending: (.+)', line)
            if match:
                events_sent[match.group(2)] = int(match.group(1))
                events_sent_count += 1
                continue
            if re.match(r'\d+ - Time given was smaller than current time', line):
                state = State.late

        file.seek(pos)
        if events_sent_count != len(local_deltas):
            print(file)
            print(events_sent_count, len(local_deltas))
        return textiter(file), result, events_sent_count, state

    it, end_at, evts_sent, state = find_end()
    messages_sent = match_line(r'\d+ - Events sent: (\d+)')
    if not messages_sent:
        return Stats(State.dead, start_at, end_at, end_at - start_at, evts_sent, None), events_sent, \
               events_delivered, local_deltas
    messages_received = match_line(r'\d+ - Events received: (\d+)')

    return Stats(state, start_at, end_at, end_at - start_at, messages_sent, messages_received), events_sent, \
           events_delivered, local_deltas


def all_stats(files):
    print('Importing files...')
    bar = progressbar.ProgressBar()
    file_stats = []
    local_deltas = []
    events_sent = {}
    events_delivered = {}
    for file in bar(files):
        with open(file, 'r') as f:
            file_stat, events_sent_temp, events_delivered_temp, local_deltas_temp = extract_stats(f)
            file_stats.append(file_stat)
            events_sent.update(events_sent_temp)
            for event, time in events_delivered_temp.items():
                if event in events_delivered:
                    events_delivered[event].append(time)
                else:
                    events_delivered[event] = [time]
            local_deltas += local_deltas_temp
    return file_stats, events_sent, events_delivered, local_deltas


def global_time(experiment_nb, stats):
    for i in range(experiment_nb):
        start_index = i * perfect_length
        end_index = start_index + perfect_length
        tmp = stats[start_index:end_index]
        mininum_start = min([stat.start_at for stat in tmp])
        maximum_end = max([stat.end_at for stat in tmp])
        yield (maximum_end - mininum_start)


stats = []
chunk = list(map(lambda x: x.tolist(), np.array_split(np.array(args.files), 4)))
with multiprocessing.Pool(processes=4) as pool:
    for result, events_sent_stats, events_delivered_stats, local_deltas_stats in pool.map(all_stats, chunk):
        stats += result
        local_deltas += local_deltas_stats
        events_sent_time.update(events_sent_stats)
        for event, times in events_delivered_stats.items():
            if event in events_delivered:
                events_delivered[event] += times
            else:
                events_delivered[event] = times

perfect_stats = [stat for stat in stats if stat.state == State.perfect]
late_stats = [stat for stat in stats if stat.state == State.late]
dead_stats = [stat for stat in stats if stat.state == State.dead]

stats_length = len(stats) / experiments_nb
perfect_length = len(perfect_stats) / experiments_nb
late_length = len(late_stats) / experiments_nb
dead_length = len(dead_stats) / experiments_nb

if not stats_length.is_integer() or not perfect_length.is_integer() \
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
stats_events_sent = []
for i in range(experiments_nb):
    start_index_sent = i * stats_length
    end_index_sent = start_index_sent + stats_length
    start_index_received = i * perfect_length
    end_index_received = start_index_received + perfect_length
    events_sent = sum(messages_sent[start_index_sent:end_index_sent])
    events_received = sum(messages_received[start_index_received:end_index_received]) / perfect_length
    stats_events_sent.append(events_sent)
    print("Experiment %d:" % (i + 1))
    print("Total events sent: %d" % events_sent)
    print("Total events received on average: %f" % events_received)
    print("Ratio events received/sent: {:.10g}".format(events_received / events_sent))
    print("-------------------------------------------")
    all_delivered.append(events_sent == events_received)


def check_list_all_identical(lst):
    return not lst or [lst[0]] * len(lst) == lst


if check_list_all_identical(all_delivered):
    print("All events sent were delivered in every experiments")
else:
    for idx, result in enumerate(all_delivered):
        if not result:
            print("Experiment %d didn't deliver every event sent" % idx)

with open('local-time-stats.csv', 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, ['local_time'])
    writer.writeheader()
    print('Writing local times to csv file...')
    bar = progressbar.ProgressBar()
    for duration in bar(durations):
        writer.writerow({'local_time': duration})

with open('global-time-stats.csv', 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, ['global_time'])
    writer.writeheader()
    print('Writing global times to csv file...')
    bar = progressbar.ProgressBar()
    for duration in bar(global_times):
        writer.writerow({'global_time': duration})

with open('local-delta-stats.csv', 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, ['delta'])
    writer.writeheader()
    print('Writing local deltas to csv file...')
    bar = progressbar.ProgressBar()
    for delta in bar(local_deltas):
        writer.writerow({'delta': delta})

with open('global-delta-stats.csv', 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, ['delta'])
    writer.writeheader()
    print('Writing global deltas to csv file...')
    bar = progressbar.ProgressBar()
    for event, time in bar(events_sent_time.items()):
        times = events_delivered[event]
        deltas = [a_time - time for a_time in times]
        for delta in deltas:
            writer.writerow({'delta': delta})

with open('event-sent-stats.csv', 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, ['events-sent'])
    writer.writeheader()
    print('Writing events sent to csv file...')
    bar = progressbar.ProgressBar()
    for event_sent in stats_events_sent:
        writer.writerows({'events-sent': event_sent})
