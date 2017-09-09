#!/usr/bin/env python
# -*- coding: utf-8 -*-
import platform
import psutil
import signal
import socket
import sys
import time

import uptime

from sibus_lib import BusElement, sibus_init, MessageObject

SERVICE_NAME = "system.monitor"
logger, cfg_data = sibus_init(SERVICE_NAME)


def get_sysmon():
    sysmon_data = {
        "system": {
            "name": None,
            "node": None,
            "release": None,
            "processor": None,
            "uptime": -1,
            "hostname": None
        },
        "ram": {
            "total": -1,
            "used": -1,
            "free": -1,
            "usage": -1
        },
        "swap": {
            "total": -1,
            "used": -1,
            "free": -1,
            "usage": -1
        },
        "fs": {
            "total": -1,
            "used": -1,
            "free": -1,
            "usage": -1
        },
        "cpu": {
            "usage": [],
            "global": -1
        },
    }

    system, node, release, version, machine, processor = platform.uname()

    sysmon_data["system"]["name"] = system
    sysmon_data["system"]["node"] = node
    sysmon_data["system"]["release"] = release
    sysmon_data["system"]["processor"] = processor

    sysmon_data["system"]["uptime"] = uptime.uptime()
    sysmon_data["system"]["hostname"] = socket.getfqdn()

    sysmon_data["cpu"]["global"] = psutil.cpu_percent(interval=1)
    sysmon_data["cpu"]["usage"] = psutil.cpu_percent(interval=1, percpu=True)

    ram_data = psutil.virtual_memory()
    sysmon_data["ram"]["free"] = ram_data.available
    sysmon_data["ram"]["total"] = ram_data.total
    sysmon_data["ram"]["used"] = ram_data.used
    sysmon_data["ram"]["usage"] = float(ram_data.used) / float(ram_data.total) * 100.0

    swap_data = psutil.swap_memory()
    sysmon_data["swap"]["free"] = swap_data.free
    sysmon_data["swap"]["total"] = swap_data.total
    sysmon_data["swap"]["used"] = swap_data.used
    sysmon_data["swap"]["usage"] = float(swap_data.used) / float(swap_data.total) * 100.0

    print psutil.disk_partitions()


    fs_data = psutil.disk_usage('/')
    sysmon_data["fs"]["free"] = fs_data.free
    sysmon_data["fs"]["total"] = fs_data.total
    sysmon_data["fs"]["used"] = fs_data.used
    sysmon_data["fs"]["usage"] = float(fs_data.used) / float(fs_data.total) * 100.0

    return sysmon_data

#http://www.anites.com//2013/12/zmq-messaging-system-lala-pi.html

sysmon_busclient = BusElement(SERVICE_NAME)
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
except KeyboardInterrupt:
    logger.info("Ctrl+C detected !")
except Exception as e:
    sysmon_busclient.stop()
    logger.exception("Program terminated incorrectly ! " + str(e))
    sys.exit(1)
finally:
    sigterm_handler()
