#!/usr/bin/env python3

from matplotlib import pyplot as plt
import json
import numpy as np

data = [json.loads(l) for l in open('test_results.log', 'r')]

goodputs = []
for test in data:
    goodputs.extend(test['goodputs'])

plt.hist(goodputs)
plt.title(f'Designed protocol goodput distribution n={len(goodputs)}')
plt.xlabel('Goodput sample mean (bytes/sec)')
plt.ylabel('Frequency')
plt.savefig('plot.png')