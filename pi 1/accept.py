#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

def ac():
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("192.168.43.86",12345))
    sock.listen(5)
    while True:
        connection,address = sock.accept()
        try:
            buf = connection.recv(8)
        except socket.timrout:
            print 'time out'
        connection.close()

if __name__ == '__main__':
    ac();
