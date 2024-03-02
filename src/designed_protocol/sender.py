#!/usr/bin/env python3

import argparse
import socket
import os
import math
import sys
import heapq
import time

import configparser

import threading

from monitor import Monitor, format_packet
from com     import Packet

# TODO: change basic list to heapq based on packet id
class Ack_buff():
    def __init__(self):
        self._packets = []
        self._lock = threading.Lock()
    def pop(self) -> Packet:
        val = None
        with self._lock:
            if len(self._packets) > 0:
                val = self._packets.pop(0)
        return val
    def get(self, n=None):
        val = None
        with self._lock:
            if len(self._packets) > 0:
                if n == None:
                    val = self._packets[0]
                else:
                    for v in self._packets:
                        if v.id == n:
                            val = v
                            break
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
                self._packets[0].id
        return c
    def remove(self, packet_num:int):
        with self._lock:
            del_pkt = None
            new_list    = []
            for p in self._packets:
                if p.id == packet_num:
                    del_pkt = p
                else:
                    new_list.append(p)
            if del_pkt:
                self._packets = new_list
        return del_pkt

    def cycle(self):
        with self._lock:
            if len(self._packets) > 0:
                pkt = self._packets.pop(0)
                pkt.reset_age()
                self._packets.append(pkt)

class Sender(Monitor):
    def __init__(self, cfg_path):
        super().__init__(cfg_path, 'sender')
        cfg = configparser.RawConfigParser(allow_no_value=True)
        cfg.read(cfg_path)
        self.recv_id       = int(cfg.get('receiver', 'id'))
        self.packet_queue  = []
        self.buffer        = Ack_buff()
        self.ppbw          = (self.Config.MAX_PACKET_SIZE / self.Config.LINK_BANDWIDTH) 

        self.rtt           = (self.ppbw + 2 * float(cfg.get('network', 'PROP_DELAY')))
        self.timeout       = 2 * self.rtt
        self.cong_thresh   = int(self.rtt / self.ppbw)
        self.cong_thresh_max = self.cong_thresh * 1.75
        self.window_sz     = self.cong_thresh
        self.is_buff_only  = False
        self.socketfd.settimeout(self.timeout)
    def __str__(self, blocking=True):
        msg = f'Sender:\n  '
        msg += '\n  '.join([f'{k} == {v}' for (k,v) in self.__dict__.items()])
        return msg
    def send(self, pkt):
        super().send(self.recv_id, pkt.format())
        pkt.reset_age()
    def update_rtt(self, rtt:int):
        a = 0.875
        rtt     *= 1.5
        self.rtt = self.rtt * a + rtt * (1-a)

    def update_window(self, is_congested=False):
        if is_congested:
            self.cong_thresh = max(min(self.cong_thresh, self.cong_thresh_max, self.window_sz) // 2, 1)
            self.window_sz   = self.cong_thresh
        else:
            self.cong_thresh = int(min(self.rtt / 1.5 / self.ppbw, self.cong_thresh_max))
            old = self.window_sz
            if self.window_sz >= self.cong_thresh:
                self.window_sz += 1
            else:
                new = self.window_sz * 2
                if new > self.cong_thresh:
                    self.window_sz = self.cong_thresh
                else:
                    self.window_sz = new            

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

    def handle_timeouts(self, kill:threading.Event):
        while (not kill.is_set()):
            pkt = self.buffer.get()
            if pkt != None and pkt.get_age() > self.timeout:
                self.send(pkt)
                self.buffer.cycle()
                print(f'timeout: {pkt}')

    def handle_acks(self, kill:threading.Event, total_packets:int):
        acked        = set(list(range(total_packets)))
        last_ping    = time.time()

        def _send_zipup():
            for pkt_id in acked:
                pkt = self.buffer.get(pkt_id)
                if pkt and pkt.get_age() > self.rtt:
                    # print(f'resend {pkt_id}') 
                    self.send(pkt)

        while (not kill.is_set()) and (len(acked) > 0):
            # for every timeout seconds, update the window size
            if (time.time() - last_ping > self.rtt):
                self.update_window()
                last_ping = time.time()
            
            try:
                ack_sender, ack_data = self.recv(self.Config.MAX_PACKET_SIZE)
                if (ack_sender == self.recv_id):
                    ack_data = ack_data.decode()
                    ack_num = int(ack_data)                           
                    pkt = self.buffer.remove(ack_num)
                    if pkt:
                        acked.remove(ack_num)
                        self.update_rtt(pkt.get_age())
                    
                    if self.is_buff_only:
                        _send_zipup()
                        self.is_buff_only = False

            except socket.timeout:
                pkt = self.buffer.get()
                if pkt != None:
                    self.send(pkt)
                    self.update_window(is_congested=True)
                    _send_zipup()
                    print(f'timeout: {pkt}')
                else:
                    print(f'timeout on EMPTY')

    def run(self):
        total_packets = self.get_packets()
        
        ack_killer    = threading.Event()
        ack_handler   = threading.Thread(target=self.handle_acks, args=(ack_killer,total_packets))
        ack_handler.start()

        timeout_killer  = threading.Event()
        timeout_handler = threading.Thread(target=self.handle_timeouts, args=(timeout_killer,))
        timeout_handler.start()

        while len(self.packet_queue) > 0:
            if self.buffer.size() < self.window_sz:
                pkt = self.packet_queue.pop(0)
                self.send(pkt)
                self.buffer.push(pkt)
                print(f'{pkt} -> buff_sz[{self.buffer.size()}]')
        self.is_buff_only = True
        
        # wait for the buffer to clear
        print('waiting for the buffer to clear')
        while self.buffer.size() > 0:
            pass
        ack_killer.set()
        timeout_killer.set()
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
