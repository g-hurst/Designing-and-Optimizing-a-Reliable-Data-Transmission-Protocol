#!/usr/bin/env python3

import subprocess as sp
import threading
import os
import re
import json
import numpy as np
import time

def parse_sender(cwd):
    f_path = os.path.join(cwd, 'sender_monitor.log')
    with open(f_path, 'r') as f:
        data = f.read()
    
    matches = re.findall(r'Goodput\s*:\s*(\d+\.\d+)\s*bytes/sec', data)
    if matches:
        gp = float(matches[0])
    else:
        gp =  None
    matches = re.findall(r'Overhead\s*:\s*(\d+)\s*bytes', data)
    if matches:
        oh = float(matches[0])
    else:
        oh =  None
    return (gp, oh)

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
    cfg_name = 'testing_config.ini'
    cwd      = '../src/designed_protocol'
    cfg_path = os.path.join('../../test_config/', cfg_name)
    
    n = 5
    goodputs       = []
    overheads      = []
    dropped_pkts   = []
    reordered_pkts = []
    start_time = time.time()
    for i in range(n):
        run_test(cfg_path, cwd)
        time_diff            = time.time() - start_time 
        gp, oh               = parse_sender(cwd)
        drop_pkts, rord_pkts = parse_emulator(cwd)
        
        goodputs.append(gp)
        overheads.append(oh)
        dropped_pkts.append(drop_pkts)
        reordered_pkts.append(rord_pkts)
        
        print(f'[{round(time_diff,3)}]: test ({i+1}/{n}) -> {gp} bytes/sec, {oh} bytes')

    print(f'goodput:  {np.mean(goodputs)}[{np.std(goodputs)}]')
    print(f'overhead: {np.mean(overheads)}[{np.std(overheads)}]')

    with open('./test_results.log', 'a') as f:
        results = {'goodputs':goodputs,
                    'overheads':overheads,
                    'dropped_pkts':dropped_pkts,
                    'reordered_pkts':reordered_pkts
                }
        results = {'description':'FILL_ME', 'results':results}
        f.write(json.dumps(results))
        f.write('\n')

if __name__ == '__main__':
    main()
