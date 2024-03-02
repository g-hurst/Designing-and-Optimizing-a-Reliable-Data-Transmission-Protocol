#!/usr/bin/env python3

import argparse
import socket
import threading
import time
import copy

import configparser

from monitor import Monitor, format_packet
from com     import Packet

class Writer(threading.Thread):
    def __init__(self, f_name):
        super().__init__()
        self._packets      = {}
        self._packets_lock = threading.Lock()
        self._stay_alive   = threading.Event()
        self._f_name       = f_name
        self.pkt_curr      = 0
        self.curr_spin     = False
        self.to_push       = None
    def run(self):
        self._stay_alive.set()
        open(self._f_name, 'wb').close()
        try:
            while self._stay_alive.is_set():
                total    = 9999
                do_write = False
                data = None
                pkt = self.packets_pop(self.pkt_curr)
                while pkt:
                    self.curr_spin = True
                    self.pkt_curr += 1
                    do_write = True
                    total = pkt.total
                    if data == None:
                        data = pkt.data
                    else:
                        data += pkt.data
                    pkt = self.packets_pop(self.pkt_curr)
                
                self.curr_spin = False
                if do_write:
                    print(f'writing -> {self.pkt_curr}/{total}')
                    with open(self._f_name, 'ab') as f:
                        f.write(data)
                    
                if self.pkt_curr == total and self.packets_size() == 0:
                    print(f'killing at {self.pkt_curr}/{total}')
                    self.kill()
                    
        except KeyboardInterrupt:
            print('keyboard interrupt in writer loop'.upper())
            self.kill()
    def kill(self):
        self._stay_alive.clear()  
    def packets_pop(self, n:int) -> Packet:
        val = None
        with self._packets_lock:
            if n in self._packets:
                val = self._packets.pop(n)
        return val
    def packets_push(self, packet: Packet):
        if self.to_push == None:
            self.to_push = set(list(range(packet.total)))
        pushed = 0
        with self._packets_lock:
            if (packet.id in self.to_push) and (packet.id not in self._packets):
                self.to_push.remove(packet.id)
                pushed = 1
                self._packets[packet.id] = packet
        return pushed
    def packets_size(self) -> int:
        with self._packets_lock:
            sz = len(self._packets)
        return sz
    def packets_curr(self):
        while self.curr_spin and self._stay_alive.is_set():
            pass    
        with self._packets_lock:
            curr = self.pkt_curr
            sz   = len(self._packets)
        return curr, sz

class Receiver(Monitor, threading.Thread):
    def __init__(self, cfg_path):
        Monitor.__init__(self, cfg_path, 'receiver')
        threading.Thread.__init__(self)
        cfg = configparser.RawConfigParser(allow_no_value=True)
        cfg.read(cfg_path)
        self.send_id       = int(cfg.get('sender', 'id'))
        self.out_file      = cfg.get('receiver', 'write_location')
        self.window_sz     = int(cfg.get('sender',   'window_size'))
        self.timeout       = (self.Config.MAX_PACKET_SIZE / self.Config.LINK_BANDWIDTH) + 2 * float(cfg.get('network', 'PROP_DELAY'))
        self._stay_alive   = threading.Event()
        self.writer        = Writer(self.out_file)
        self.writer.start()
    def __str__(self, blocking=True):
        msg = f'Reciever:\n  '
        msg += '\n  '.join([f'{k} == {v}' for (k,v) in self.__dict__.items()])
        return msg

    def run(self):
        self._stay_alive.set()
        packets_recieved = 0
        while self._stay_alive.is_set():
            try:
                recv_sender, recv_data = self.recv(self.Config.MAX_PACKET_SIZE)
                if recv_sender == self.send_id:
                    pkt = Packet(recv_data, is_bytes=True)
                    packets_recieved += self.writer.packets_push(pkt)
                    ack_bytes = f'{pkt.id}'.encode() 
                    self.send(self.send_id, ack_bytes)

                if packets_recieved == pkt.total:
                    self.recv_end(self.out_file, self.send_id)
                    self.kill()
            except socket.timeout:
                print('timeout occurred in reciever')
        
        # hang out for any missed packets in the end
        start_time = time.time()
        timeout   = self.timeout * self.window_sz
        self.socketfd.settimeout(timeout)
        while time.time() - start_time < timeout:
            try:
                recv_sender, recv_data = self.recv(self.Config.MAX_PACKET_SIZE)
                pkt = Packet(recv_data, is_bytes=True)
                ack_bytes = f'{pkt.id}'.encode() 
                self.send(self.send_id, ack_bytes)
                start_time = time.time()
            except socket.timeout:
                break

    def kill(self):
        self._stay_alive.clear()  

def main():
    parser = argparse.ArgumentParser(
                        prog='receiver_stop_and_go.py',
                        description='Receiver for stop and go protocol')
    parser.add_argument('config_path', 
                        type=str, 
                        help='path of the config file')
    args = parser.parse_args()

    receiver = Receiver(args.config_path)
    print(receiver)
    receiver.start()

if __name__ == '__main__':
    main()
