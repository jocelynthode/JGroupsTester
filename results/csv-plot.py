#!/usr/bin/env python3.5
import argparse
import matplotlib.pyplot as plt
import pandas as pd

parser = argparse.ArgumentParser(description='Generate plots for bytes logs')
parser.add_argument('file', metavar='FILE', type=argparse.FileType('r'),
                    help='the file to parse')
parser.add_argument('-n', '--name', type=str, help='the name of the file to write the result to',
                    default='plot.png')
args = parser.parse_args()

df = pd.read_csv(args.file)


df.plot()
plt.savefig(args.name)

