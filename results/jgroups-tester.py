#!/usr/bin/env python3.5
import re
import sys
from pathlib import Path
from itertools import islice
from collections import namedtuple

length = 0

Stats = namedtuple('Stats', ['duration', 'sent', 'received', 'sent_bytes', 'received_bytes'])


def extract_stats(lines):
    it = iter(lines)  # Force re-use of same iterator
    end_at = 0
    start_at = 0
    for line in it:
        match = re.match(r'(\d+) - Sending:', line)
        if match:
            start_at = int(match.group(1))
            break
    for line in it:
        match = re.match(r'(\d+) - All events delivered !', line)
        if match:
            end_at = int(match.group(1))
            break

    def extract_int(a_line):
        return int(re.findall(r' [0-9]+$', a_line)[0])

    sent, received, sent_bytes, received_bytes = (
        extract_int(line) for line in islice(it, 0, 4)
    )

    return Stats(end_at - start_at, sent, received, sent_bytes, received_bytes)


def all_stats():
    for fpath in Path().glob(sys.argv[1]+'/**/172.*.txt'):
        global length
        length += 1
        with fpath.open() as f:
            yield extract_stats(f)

stats = list(all_stats())
durations = [stat.duration for stat in stats]
mininum = min(durations)
maximum = max(durations)
average = sum(durations) / len(durations)

# print(durations)
print("JGroups run with %d peers" % length)
print("------------------------")
print("Least time to deliver: %d ms" % mininum)
print("Most time to deliver: %d ms" % maximum)
print("Average time to deliver: %d ms" % average)
print("Total number of messages sent: %d" % sum([stat.sent for stat in stats]))
print("Total number of bytes sent: %d" % sum([stat.sent_bytes for stat in stats]))
print("Total number of messages received: %d" % sum([stat.received for stat in stats]))
print("Total number of bytes received: %d" % sum([stat.received_bytes for stat in stats]))
