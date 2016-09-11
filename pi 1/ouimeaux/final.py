#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import bluetooth

from ouimeaux.environment import Environment
from ouimeaux.utils import matcher
from ouimeaux.signals import receiver, statechange, devicefound

def on_switch(switch):
    print"switch found"
env = Environment(on_switch)

def ac():
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("10.22.22.110", 12345))
    sock.listen(5)
    while True:
        connection,address = sock.accept()
        try:
            buf = connection.recv(8)
            print buf
            if buf == '1':
                for switch in ( env.list_switches() ):
                    print "Turning On: " + switch
                    env.get_switch( switch ).on()
            else:
                for switch in ( env.list_switches() ):
                    print "Turning Off: " + switch
                    env.get_switch( switch ).off()
        except socket.timeout:
            print 'time out'
        connection.close()


if __name__ == '__main__':
    n = 99
    while n>0:
        n = n-2
        server_sock=bluetooth.BluetoothSocket(bluetooth.RFCOMM)

        port = 1
        server_sock.bind(("",port))
        server_sock.listen(1)

        client_sock,address = server_sock.accept()
        print "Accepted connection from",address

        data = client_sock.recv(5)
        print "received{%s}" % data
        print data

        env.start()
        if data == '12321':
            for switch in ( env.list_switches() ):
                print "Turning On: "
                env.get_switch( switch ).on()
        else:
            for switch in ( env.list_switches() ):
                print "Turning Off: "
                env.get_switch( switch ).off()
