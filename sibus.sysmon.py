#!/usr/bin/env python
# -*- coding: utf-8 -*-
import platform
import signal
import socket
import sys
import time

import psutil
import uptime

from sibus_lib import BusElement, sibus_init, MessageObject
from sibus_lib.utils import datetime_now_float

SERVICE_NAME = "system.monitor"
logger, cfg_data = sibus_init(SERVICE_NAME)

LAST_COUNTERS = {}


def counter_delta(timestamp, address, direction, current_counter):
    fa = address + "/" + direction

    if fa not in LAST_COUNTERS:
        LAST_COUNTERS[fa] = (timestamp, current_counter)
        return -1
    else:
        (last_timestamp, last_counter) = LAST_COUNTERS[fa]
        counter_delta = current_counter - last_counter
        time_delta = timestamp - last_timestamp
        return counter_delta / time_delta


def get_sysmon():
    sysmon_data = {}

    system, node, release, version, machine, processor = platform.uname()

    sysmon_data["hostname"] = socket.getfqdn()

    sysmon_data["system"] = {}
    sysmon_data["system"]["name"] = system
    sysmon_data["system"]["node"] = node
    sysmon_data["system"]["release"] = release
    sysmon_data["system"]["processor"] = processor
    sysmon_data["system"]["uptime"] = uptime.uptime()
    sysmon_data["system"]["hostname"] = socket.getfqdn()

    sysmon_data["cpu"] = {}
    sysmon_data["cpu"]["global"] = psutil.cpu_percent(interval=1)
    sysmon_data["cpu"]["usage"] = psutil.cpu_percent(interval=1, percpu=True)

    ram_data = psutil.virtual_memory()
    sysmon_data["ram"] = {}
    sysmon_data["ram"]["free"] = ram_data.available
    sysmon_data["ram"]["total"] = ram_data.total
    sysmon_data["ram"]["used"] = ram_data.used
    sysmon_data["ram"]["usage"] = float(ram_data.used) / float(ram_data.total) * 100.0

    swap_data = psutil.swap_memory()
    sysmon_data["swap"] = {}
    sysmon_data["swap"]["free"] = swap_data.free
    sysmon_data["swap"]["total"] = swap_data.total
    sysmon_data["swap"]["used"] = swap_data.used
    sysmon_data["swap"]["usage"] = float(swap_data.used) / float(swap_data.total) * 100.0

    sysmon_data["filesystem"] = []
    for part in psutil.disk_partitions():
        fs_data = {
            "mountpoint": part.mountpoint,
            "device": part.device,
            "fstype": part.fstype,
        }
        tmp = psutil.disk_usage(part.mountpoint)
        fs_data["free"] = tmp.free
        fs_data["total"] = tmp.total
        fs_data["used"] = tmp.used
        fs_data["usage"] = float(tmp.used) / float(tmp.total) * 100.0

        sysmon_data["filesystem"].append(fs_data)

    sysmon_data["network"] = []
    intfs = psutil.net_if_addrs()
    counters = psutil.net_io_counters(pernic=True)
    for part in intfs:
        if part == "lo":
            continue
        for snic in intfs[part]:
            if snic.family == socket.AF_INET:
                net_data = {
                    "address": snic.address,
                    "netmask": snic.netmask,
                    "interface": part,
                    "bytes_recv": counter_delta(datetime_now_float(), snic.address, "RECV", counters[part].bytes_recv),
                    "bytes_sent": counter_delta(datetime_now_float(), snic.address, "SENT", counters[part].bytes_sent),
                }
                sysmon_data["network"].append(net_data)


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
        message = MessageObject(data=get_sysmon(), topic="info.system.monitor")
        sysmon_busclient.publish(message)
        time.sleep(10)
except KeyboardInterrupt:
    logger.info("Ctrl+C detected !")
except Exception as e:
    sysmon_busclient.stop()
    logger.exception("Program terminated incorrectly ! " + str(e))
    sys.exit(1)
finally:
    sigterm_handler()
