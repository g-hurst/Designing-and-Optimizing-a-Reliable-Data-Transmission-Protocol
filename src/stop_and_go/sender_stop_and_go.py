#!/usr/bin/env python3

import argparse
import socket
import os
import math
import sys

import configparser
from tqdm import tqdm

import threading

from monitor import Monitor, format_packet


class Sender(Monitor):
    def __init__(self, cfg_path):
        super().__init__(cfg_path, 'sender')
        self.cfg = configparser.RawConfigParser(allow_no_value=True)
        self.cfg.read(cfg_path)
        self.recv_id = int(self.cfg.get('receiver', 'id'))
        self.packet_queue = {}
        timeout = (self.Config.MAX_PACKET_SIZE / self.Config.LINK_BANDWIDTH) + 2 * float(self.cfg.get('network', 'PROP_DELAY'))
        self.socketfd.settimeout(timeout)
    def __str__(self, blocking=True):
        msg = f'Sender:\n  '
        msg += '\n  '.join([f'{k} == {v}' for (k,v) in self.__dict__.items()])
        return msg
    def get_packets(self):
        # TODO: when a file is VERY large, will run out of 
        #       memory with this method
        packet_num_byt = (str((sys.maxsize,sys.maxsize)) + '|').encode()
        packet_header  = format_packet(self.id, self.recv_id, b'')  
        packet_data_sz = self.Config.MAX_PACKET_SIZE - (len(packet_header) + len(packet_num_byt))
        total_packets  = math.ceil(os.path.getsize(self.file) / packet_data_sz)
        with open(self.file, 'rb') as f:
            for i in range(total_packets):
                packet_num_byt = (str((i,total_packets)) + '|').encode()
                chunk = packet_num_byt + f.read(packet_data_sz)
                self.packet_queue[i] = chunk

    def run(self):
        self.get_packets()
        curr_packet_num = 0
        with tqdm(total=len(self.packet_queue)) as pbar:
            while len(self.packet_queue) > 0:
                try:   
                    self.send(self.recv_id, self.packet_queue[curr_packet_num])
                    ack_sender, ack_data = self.recv(self.Config.MAX_PACKET_SIZE)
                    if (ack_sender == self.recv_id) and (int(ack_data.decode())  == curr_packet_num):
                        self.packet_queue.pop(curr_packet_num)
                        curr_packet_num += 1
                        pbar.update(1)
                except socket.timeout:
                    print(f'timeout occured: resending packet[{curr_packet_num}]')
        
        self.send_end(self.recv_id)

def main():
    parser = argparse.ArgumentParser(
                        prog='receiver_stop_and_go.py',
                        description='Reciever for stop and go protocol')
    parser.add_argument('config_path', 
                        type=str, 
                        help='path of the config file')
    args = parser.parse_args()    

    sender = Sender(args.config_path)
    print(sender)
    sender.run()

if __name__ == '__main__':
    main()