#!/usr/bin/env python3

import subprocess as sp
import threading
import argparse
import os
import re
import json

def parse_sender(cwd):
    f_path = os.path.join(cwd, 'sender_monitor.log')
    with open(f_path, 'r') as f:
        data = f.read()
    
    matches = re.findall(r'Goodput\s*:\s*(\d+\.\d+)\s*bytes/sec', data)
    if matches:
        return float(matches[0])
    else:
        return None

def parse_emulator(cwd):
    f_path = os.path.join(cwd, 'emulator.log')
    with open(f_path, 'r') as f:
        data = f.read()

    reordered_pkts = data.count('Reordered Packet')
    dropped_pkts   = data.count('Dropped Packet')
    return (dropped_pkts, reordered_pkts)

def run_test(config_file, cwd, log=False):
    def run_cmd(cmd):
        out = sp.run(cmd, shell=True, stdout=sp.PIPE, stderr=sp.STDOUT, cwd=cwd)
        if log:
            if out.returncode != 0:
                print('ERROR RUNNING:', out.args)
                print(out.stdout.decode())
                print()
            else:
                print('SUCCESS RUNNING:', out.args)

    commands = [
        f'make run-receiver config={config_file}',
        f'make run-sender config={config_file}',
        f'python3 ../../emulator/emulator.py {config_file}'
    ]

    threads = []
    for cmd in commands:
        thread = threading.Thread(target=run_cmd, args=(cmd,))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()

def main():
    cfg_name = 'config3.ini'
    cwd      = '../src/designed_protocol'
    cfg_path = os.path.join('../../test_config/', cfg_name)
    
    n=10
    goodputs       = []
    dropped_pkts   = []
    reordered_pkts = []
    for i in range(n):
        run_test(cfg_path, cwd)
        gp  = parse_sender(cwd)
        drop_pkts, rord_pkts = parse_emulator(cwd)
        goodputs.append(gp)
        dropped_pkts.append(drop_pkts)
        reordered_pkts.append(rord_pkts)
        print(f'test ({i+1}/{n}) -> {gp} bytes/sec')

    with open('./test_results.log', 'a') as f:
        results = {'goodputs':goodputs,
                    'dropped_pkts':dropped_pkts,
                    'reordered_pkts':reordered_pkts
                }
        f.write(json.dumps(results))
        f.write('\n')

if __name__ == '__main__':
    main()
