import matplotlib
import matplotlib.pyplot as plt
import re
import os
from subprocess import Popen
import socket
from threading import Thread
from typing import Dict, List
from src.senders import Sender
from os.path import join


RECEIVER_FILE = "run_receiver.py"
AVERAGE_SEGMENT_SIZE = 80
QUEUE_LOG_FILE = "downlink_queue.log"
QUEUE_LOG_TMP_FILE = "downlink_queue_tmp.log"

DROP_LOG = "debug_log.log"
DROP_LOG_TMP_FILE = "debug_log_tmp.log"

def get_open_udp_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

SENDER_COLORS = ["blue", "red", "green", "cyan", "magenta", "yellow", "black"]


def run_with_mahi_settings(
        mahimahi_settings: Dict, 
        seconds_to_run: int, 
        senders: List, 
        should_print_performance: bool , 
        episode_num : int,
        write_to_disk : bool ,
        output_dir : str,
        experiment_dir : str
        ):
    mahimahi_cmd = generate_mahimahi_command(mahimahi_settings)

    sender_ports = " ".join(["$MAHIMAHI_BASE %s" % sender.port for sender in senders])

    cmd = "%s -- sh -c 'python3 %s %d %s' > out.out" % (mahimahi_cmd, RECEIVER_FILE, seconds_to_run, sender_ports)
    Popen(cmd, shell=True)
    for sender in senders:
        sender.handshake()
    threads = [Thread(target=sender.run, args=[seconds_to_run]) for sender in senders]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    os.rename(QUEUE_LOG_FILE, QUEUE_LOG_TMP_FILE)
    #os.rename(DROP_LOG, DROP_LOG_TMP_FILE)

    Popen("pkill -f mm-link", shell=True).wait()
    Popen("pkill -f run_receiver", shell=True).wait()
