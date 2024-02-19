#!/usr/bin/env python3

import argparse
import socket
import threading

import configparser

from monitor import Monitor, format_packet

class Packet():
    def __init__(self, data):
        data = data.split(b'|', maxsplit=1)
        data[0] = list(map(int, (data[0]
                    .decode()
                    .replace(' ', '')
                    .replace('(', '')
                    .replace(')', '')
                    .split(',')
                    )))
        self.id  = data[0][0]
        self.total = data[0][1]
        self.data = data[1]
    def __repr__(self):
        return f'Packet<{self.id}/{self.total}>'
    def __lt__(self, other):
        return self.id < other.id


class Writer(threading.Thread):
    def __init__(self, f_name):
        super().__init__()
        self._packets = {}
        self._packets_lock = threading.Lock()
        self._stay_alive   = threading.Event()
        self._f_name = f_name
    def run(self):
        self._stay_alive.set()
        open(self._f_name, 'wb').close()
        try:
            pkt_curr = 0
            while self._stay_alive.is_set():
                pkt = self.packets_pop(pkt_curr)
                if pkt != None:
                    with open(self._f_name, 'ab') as f:
                        f.write(pkt.data)
                    if pkt.id + 1 == pkt.total:
                        self.kill()
                    pkt_curr += 1

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
        with self._packets_lock:
            self._packets[packet.id] = packet
    def packets_size(self) -> int:
        with self._packets_lock:
            sz = len(self._packets)
        return sz

class Receiver(Monitor, threading.Thread):
    def __init__(self, cfg_path):
        Monitor.__init__(self, cfg_path, 'receiver')
        threading.Thread.__init__(self)
        self.cfg = configparser.RawConfigParser(allow_no_value=True)
        self.cfg.read(cfg_path)
        self.send_id = int(self.cfg.get('sender', 'id'))
        self.file    = self.cfg.get('receiver', 'write_location')
        self.writer  = Writer(self.file)
        self.writer.start()
        self._stay_alive   = threading.Event()
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
                pkt = Packet(recv_data)
                print(f'got packet {pkt.id}')
                if pkt.id == packets_recieved:
                    self.writer.packets_push(pkt)
                    packets_recieved += 1
                if pkt.id <= packets_recieved:
                    self.send(self.send_id, f'{pkt.id}'.encode())
                if packets_recieved == pkt.total:
                    self.kill()
            except socket.timeout:
                print('timeout occurred')
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
    receiver.start()

if __name__ == '__main__':
    main()