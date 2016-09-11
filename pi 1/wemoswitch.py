#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from ouimeaux.environment import Environment
from ouimeaux.utils import matcher
from ouimeaux.signals import receiver, statechange, devicefound

def on_switch(switch):
    print"switch found"
env = Environment(on_switch)
if __name__ == '__main__':
    env.start()
    #env.discover(seconds=5)
    #on_switch
    #env.list_switches()
    #switch.explain();
   # for switch in ( env.list_switches() ):
    #        print "Turning On: " + switch
     #       env.get_switch( switch ).on()
    for switch in ( env.list_switches() ):
            print "Turning Off: " + switch
            env.get_switch( switch ).off()
