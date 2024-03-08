#!/usr/bin/env python3

import argparse
import socket
import os
import math
import sys
import time
from collections import OrderedDict

import configparser

import threading
from multiprocessing import Process, Queue
from multiprocessing.managers import BaseManager

from monitor import Monitor, format_packet
from com     import Packet

class Ack_buff():
    def __init__(self):
        self._packets = OrderedDict()
        self._lock = threading.Lock()
    def pop(self) -> Packet:
        val = None
        with self._lock:
            if len(self._packets) > 0:
                val = self._packets.popitem(last=True)[1]
        return val
    def get(self, id=None):
        val = None
        with self._lock:
            if len(self._packets) > 0:
                if id != None:
                    val = self._packets.get(id, None)
                elif len(self._packets) > 0:
                    val = next(iter(self._packets.values()))

            return val
    def push(self, packet: Packet):
        with self._lock:
            self._packets[packet.get_id()] = packet
    def size(self) -> int:
        with self._lock:
            sz = len(self._packets)
        return sz
    def remove(self, packet_num:int):
        # print(f'removing {packet_num}')
        with self._lock:
            del_pkt  = self._packets.pop(packet_num, None)
        return del_pkt

    def cycle(self):
        with self._lock:
            if len(self._packets) > 0:
                pkt = next(iter(self._packets.values()))
                self._packets.move_to_end(pkt.get_id(), last=True)

class Sender(Monitor):
    def __init__(self, cfg_path):
        super().__init__(cfg_path, 'sender')
        cfg = configparser.RawConfigParser(allow_no_value=True)
        cfg.read(cfg_path)
        self.recv_id       = int(cfg.get('receiver', 'id'))
        self.packet_queue  = []

        BaseManager.register('Ack_buff', Ack_buff)
        BaseManager.register('Packet', Packet)
        self.manager = BaseManager()
        self.manager.start()
        self.ack_queue     = Queue()
        self.buffer        = self.manager.Ack_buff()

        self.ppbw          = (self.Config.MAX_PACKET_SIZE / self.Config.LINK_BANDWIDTH)
        self.rtt           = (self.ppbw + 2 * float(cfg.get('network', 'PROP_DELAY')))
        self.timeout       = 4 * self.rtt
        self.cong_thresh   = int(self.rtt / self.ppbw)
        self.cong_thresh_max = self.cong_thresh * 1.25
        self.window_sz     = self.cong_thresh
        self.is_buff_only  = False
        # self.socketfd.settimeout(self.timeout)
    def __str__(self, blocking=True):
        msg = f'Sender:\n  '
        msg += '\n  '.join([f'{k} == {v}' for (k,v) in self.__dict__.items()])
        return msg
    def send(self, pkt):
        super().send(self.recv_id, pkt.format())
        pkt.reset_age()
    def update_rtt(self, rtt:int):
        a = 0.875
        rtt     *= 1.65
        self.rtt     = self.rtt * a + rtt * (1-a)
        self.timeout = self.timeout * a + self.rtt * (1-a)

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
                    self.manager.Packet(((i,total_packets), f.read(packet_data_sz)), is_bytes=False)
                )
        return total_packets

    def scan_acks(self):
        while True:
            ack_sender, ack_data = self.recv(self.Config.MAX_PACKET_SIZE)
            if (ack_sender == self.recv_id):
                ack_num = int(ack_data.decode())
                self.ack_queue.put(ack_num)

    def handle_acks(self, kill:threading.Event, total_packets:int):
        ack_scanner   = Process(target=self.scan_acks)
        ack_scanner.start()

        acked       = set(list(range(total_packets)))
        fast_resent = set()
        last_ping   = time.time()

        def _send_zipup():
            for pkt_id in acked:
                pkt = self.buffer.get(id=pkt_id)
                if pkt and (pkt.get_age() > self.rtt / 2):
                    print(f'resend {pkt_id}')
                    self.send(pkt)

        while (not kill.is_set()) and (len(acked) > 0):
            # for every timeout seconds, update the window size
            if (time.time() - last_ping > self.rtt):
                self.update_window()
                last_ping = time.time()

            # remove acks and update the RTT and timeout according to the 
            # time it took to ack the given packet
            try:
                ack_num = self.ack_queue.get_nowait() # errors when queue is empty

                # remove the packet from buffer
                if ack_num in acked:
                    pkt = self.buffer.remove(ack_num)
                    if pkt:
                        acked.remove(ack_num)
                        self.update_rtt(pkt.get_age())

                # check current ack num compared to lowest packet in buffer
                # retransmit if needed
                pkt = self.buffer.get()
                if pkt and (ack_num - pkt.get_id() > 2) and (pkt.get_id() not in fast_resent):
                    print(f'fast retransmit: {pkt.get_id()}')
                    fast_resent.add(pkt.get_id())
                    self.send(pkt)
                    self.buffer.cycle()

            except:
                pass
            
            # check for timeouts
            if self.ack_queue.empty():
                pkt = self.buffer.get()
                if pkt and (pkt.get_age() > self.timeout):
                    # self.update_window(is_congested=True)
                    # self.timeout = self.timeout * 1.5
                    print(f'timeout: {pkt} age  {pkt.get_age()}')
                    self.send(pkt)
                    self.buffer.cycle()
            # else:
            #     print(f'size of ackbuff {self.ack_queue.qsize()}')


            # zip up unsent packets when no more packets can be added to buff
            # if self.is_buff_only:
            #     self.is_buff_only = False
            #     _send_zipup()

        ack_scanner.terminate()
        ack_scanner.join()

    def run(self):
        total_packets = self.get_packets()

        ack_killer    = threading.Event()
        ack_handler   = threading.Thread(target=self.handle_acks, args=(ack_killer,total_packets))
        ack_handler.start()

        while len(self.packet_queue) > 0:
            if self.buffer.size() < self.window_sz:
                pkt = self.packet_queue.pop(0)
                self.send(pkt)
                self.buffer.push(pkt)
                # print(f'{pkt} -> buff_sz[{self.buffer.size()}]')
        self.is_buff_only = True

        # wait for the buffer to clear
        print('waiting for the buffer to clear')
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
