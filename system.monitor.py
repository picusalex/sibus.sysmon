#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import psutil
import signal
import sys
import time

sys.path.append(os.getenv('ALPIBUS_DIR', os.getcwd()))

from sibus_lib.lib import mylogger
from sibus_lib.lib import BusElement, MessageObject

SERVICE_NAME = "system.monitor"
logger = mylogger(SERVICE_NAME)

def on_busmessage(message):
    logger.info(message)

def get_sysmon():
    sysmon_data = {}
    sysmon_data["cpu_percent"] = psutil.cpu_percent(interval=1)

    ram_data = psutil.virtual_memory()
    sysmon_data["ram_free"] = ram_data.free
    sysmon_data["ram_total"] = ram_data.total
    sysmon_data["ram_used"] = ram_data.used
    sysmon_data["ram_usage"] = float(ram_data.used)/float(ram_data.total)*100.0

    swap_data = psutil.swap_memory()
    sysmon_data["swap_free"] = swap_data.free
    sysmon_data["swap_total"] = swap_data.total
    sysmon_data["swap_used"] = swap_data.used
    sysmon_data["swap_usage"] = float(swap_data.used) / float(swap_data.total) * 100.0

    fs_data = psutil.disk_usage('/')
    sysmon_data["fs_free"] = fs_data.free
    sysmon_data["fs_total"] = fs_data.total
    sysmon_data["fs_used"] = fs_data.used
    sysmon_data["fs_usage"] = float(fs_data.used) / float(fs_data.total) * 100.0

    return sysmon_data

#http://www.anites.com//2013/12/zmq-messaging-system-lala-pi.html

sysmon_busclient = BusElement(SERVICE_NAME, callback=on_busmessage)
sysmon_busclient.start()

def sigterm_handler(_signo=None, _stack_frame=None):
    sysmon_busclient.stop()
    logger.info("Program terminated correctly")
    sys.exit(0)

signal.signal(signal.SIGTERM, sigterm_handler)

try:
    while 1:
        message = MessageObject(data=get_sysmon(), topic="system.monitor")
        sysmon_busclient.publish(message)
        time.sleep(5)
except (KeyboardInterrupt, SystemExit):
    logger.info("Ctrl+C detected !")
except:
    logger.error("Program terminated incorrectly ! ")
    sys.exit(1)
    pass

sigterm_handler()
