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
from com     import Packet

class Ack_buff():
    def __init__(self):
        self._packets = []
        self._lock = threading.Lock()
    def pop(self, n=0) -> Packet:
        val = None
        with self._lock:
            if len(self._packets) > 0:
                val = self._packets.pop(n)
        return val
    def get(self, n=0):
        val = None
        with self._lock:
            if len(self._packets) > 0:
                val = self._packets[n]
        return val
    def push(self, packet: Packet):
        with self._lock:
            self._packets.append(packet)
    def size(self) -> int:
        with self._lock:
            sz = len(self._packets)
        return sz
    def curr(self):
        c = None
        with self._lock:
            if len(self._packets) > 0:
                c = self._packets[0].id
        return c
    def update(self, packet_num:int):
        curr = self.curr()
        while (curr != None) and (curr <= packet_num):
            self.pop()
            curr = self.curr()

class Sender(Monitor):
    def __init__(self, cfg_path):
        super().__init__(cfg_path, 'sender')
        cfg = configparser.RawConfigParser(allow_no_value=True)
        cfg.read(cfg_path)
        self.window_sz    = int(cfg.get('sender',   'window_size'))
        self.recv_id      = int(cfg.get('receiver', 'id'))
        self.packet_queue = []
        self.buffer       = Ack_buff()
        timeout = (self.Config.MAX_PACKET_SIZE / self.Config.LINK_BANDWIDTH) + 2 * float(cfg.get('network', 'PROP_DELAY'))
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
                self.packet_queue.append(
                    Packet(((i,total_packets), f.read(packet_data_sz)), is_bytes=False)
                )
        return total_packets

    def handle_acks(self, kill:threading.Event, total_packets:int):
        while (not kill.is_set()) and (self.buffer.curr() != total_packets - 1):
            try:
                ack_sender, ack_data = self.recv(self.Config.MAX_PACKET_SIZE)
                if (ack_sender == self.recv_id):
                    ack_num = int(ack_data.decode())
                    self.buffer.update(ack_num)
            except:
                pkt = self.buffer.get(0)
                if pkt != None:
                    self.send(self.recv_id, pkt.format())
                    print(f'timeout on packet[{pkt.id}]')
                else:
                    print(f'timeout on EMPTY')

    def run(self):
        total_packets = self.get_packets()
        ack_killer    = threading.Event()
        ack_handler   = threading.Thread(target=self.handle_acks, args=(ack_killer,total_packets))
        ack_handler.start()
        with tqdm(total=total_packets) as pbar:
            while len(self.packet_queue) > 0:
                if self.buffer.size() < self.window_sz:
                    pkt = self.packet_queue.pop(0)
                    self.send(self.recv_id, pkt.format())
                    self.buffer.push(pkt)
                    pbar.update(1)
        while self.buffer.size() > 0:
            pass 
        ack_killer.set()

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
