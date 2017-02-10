#!/usr/bin/env python

import argparse
import os
import simplejson
import sys

import eventlet
import websocket
from retrying import retry

eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)

# If ../highlander_agent/__init__.py exists, add ../ to Python search path, so that
# it will override what happens to be installed in /usr/(local/)lib/python...
POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir, os.pardir, os.pardir))

if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'highlander_agent', '__init__.py')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from highlander_agent.monitor.daemon import HighlanderMonitorDaemon
import time
from highlander_agent.common.constants import Constant
from highlander_agent.notifier import send
from highlander_agent.rules import instance
from highlander_agent.common import log
from highlander_agent.common.util import AgentConfigParser
import json
from  highlander_agent.rpcclient.api import API
import timeit

LOGGER = log.getLogger(Constant.LOGGER_MONITOR)


class HypervisorMonitor(HighlanderMonitorDaemon):
    def __init__(self, pidfile, instance_configuration_json, cfg):
        HighlanderMonitorDaemon.__init__(self, pidfile, instance_configuration_json)
        self._cfg = cfg

    def run(self):
        LOGGER.info("Running hypervisor monitor for instance %s" % self._instance_id_to_monitor)
        if self._instance_configuration_json is None:
            LOGGER.error("Instance %s configuration is missing during monitoring")
        else:
            try:
                hostname = self._hypervisor_to_monitor["hostname"]
                url = "ws://" + hostname + ":3000/events"
                self._monitor_hypervisor(self.on_event, url)
            except Exception, e:
                exc_type, exc_obj, exc_tb = sys.exc_info()[:]
                LOGGER.error(
                    "Exception Hypervisor: %s, %s" % (exc_type, exc_tb.tb_lineno))
                LOGGER.error("error %r" % e)
                LOGGER.info("calling fail event")
                self.on_event("fail", "hypervisor failed event occured")

    """
    Configure timeout for hypervisor monitor in condif.cfg file
    """

    @retry(wait_fixed=1, stop_max_attempt_number=3)
    def _monitor_hypervisor(self, eventfun, url):
        LOGGER.info("Monitoring hypervisor")
        LOGGER.info(url)
        start_time = timeit.default_timer()
        LOGGER.info("Monitor start time %s" % start_time)
        self.ws = websocket.WebSocketApp(url, on_message=self.on_message)

        self.ws.run_forever()
        self.ws.send("hi")

    def on_message(self, ws, message):
        LOGGER.info("Status")
        LOGGER.info("Hypervisor Status:up")

    def on_error(self, ws, error):
        LOGGER.info("Hypervisor Status:error")

    def on_close(self, ws):
        LOGGER.info("Hypervisor status:closed")

    def _monitor_hypervisor_delete(self, eventfun):
        # from  highlander_agent.rpcclient.api import API===
        hostname = self._hypervisor_to_monitor["hostname"]
        method = self._hypervisor_to_monitor["method"]
        heartbeat_count = 0
        threshold = 3
        success_count = 0
        reset_frequency = 5

        data = {
            "method": method,
            "arg": hostname
        }
        msg = json.dumps(data)

        api = API(self._cfg, hostname)
        timeout_padding = float(self._cfg["Failover_Test"]["hypervisor_timeout_slider"])
        original_timeout = float(self._cfg["Failover_Test"]["hypervisor_timeout"])
        timeout = float(self._cfg["Failover_Test"]["hypervisor_timeout"])

        while True:
            LOGGER.info("Monitoring hypervisor")
            LOGGER.info(heartbeat_count)
            if heartbeat_count >= threshold:
                eventfun("fail", "hypervisor failed event occured")
                break;
            try:
                LOGGER.info(timeout)
                start_time = timeit.default_timer()
                LOGGER.info("Calling api")
                response = api.call(msg, timeout)
                elapsed_time = timeit.default_timer() - start_time
                LOGGER.info("<<<<<<<<<<<<<<<<>>>>>>>>>>>>>> -hypervisor status  %r" % response)
                LOGGER.info("Heartbeat API call  elapsed time %s" % elapsed_time)
                if str(response) == "1":
                    if float(elapsed_time) < float(timeout):
                        timeout = original_timeout
                    time.sleep(0.01)
                    heartbeat_count = 0
                    LOGGER.info("response %s" % response)
                else:
                    success_count = 0
                    timeout = self._slidefailuretime(timeout, timeout_padding)
                    heartbeat_count += 1
                    LOGGER.info("response %s" % response)

            except Exception, e:
                exc_type, exc_obj, exc_tb = sys.exc_info()[:]
                LOGGER.error("Exception while executing scripts: %s, %s" % (exc_type, exc_tb.tb_lineno))
                heartbeat_count += 1

    def on_event(self, event_type, event_message):
        if event_type == 'fail':
            try:
                self.on_fail_event()
            except Exception, e:
                LOGGER.error("Exception %r", e)

    """
    On failure of hypervisor
    """

    def on_fail_event(self):
        # send notification to controller
        # run rules
        LOGGER.info("FAILED FAILED FAILED")
        if self._hypervisor_to_monitor["on_fail_event"] is not None:
            LOGGER.info(self._hypervisor_to_monitor)
            for entry in self._hypervisor_to_monitor["on_fail_event"]:
                method = entry["rule"]["method"]
                arg = entry["rule"]["arg"]
                for item in self._instances:
                    if item["id"] == arg["instance_id"]:
                        target_instance = item
                        break
                    else:
                        target_instance = None
                if target_instance == None:
                    hostname = None
                    target_instance["id"] = self._hypervisor_to_monitor["hostname"]
                else:
                    hostname = target_instance["host_name"]
                try:
                    rules = instance.Rules()
                    func = getattr(instance.Rules, method)
                    if callable(func):
                        notifier = send.AgentNotifier(self._cfg, "AgentNotifier", hostname)
                        func(arg["instance_id"], arg["message"], target_instance, notifier)
                    else:
                        return {"return_code": 500, "msg": "NoSuchMethod exception occurred %s" % method}
                except Exception, e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()[:]
                    LOGGER.error(
                        "Exception while trying to start monitor for config: %s, %s" % (exc_type, exc_tb.tb_lineno))
                    return {"return_code": 500, "msg": "NoSuchMethod exception occurred %r" % e}

    def delpid(self):
        pass

    """
    1. if response is failing , attempt to double the time till failurecount is 3

    """

    def _slidefailuretime(self, timeout, padding):
        newtime = float(timeout + padding)
        return newtime


def main():
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-c", help="config: -c <json>", dest="config")
        parser.add_argument("-p", help="pidfile: -p <file name>", dest="pidfile")

        args = parser.parse_args()
        print args.config
        print args.pidfile

        cfg = AgentConfigParser()

        cfg.read(os.path.abspath(os.path.join(os.path.dirname(__file__), '../config.cfg')))
        cfg = cfg.as_dic()

        LOGGER.info("Attempting to start monitoring for config %s under pidfile %s" % (args.config, args.pidfile))

        try:
            nHypervisorMonitor = HypervisorMonitor(pidfile=args.pidfile,
                                                   instance_configuration_json=simplejson.loads(args.config),
                                                   cfg=cfg)
        except Exception, e:
            LOGGER.error("Exception while trying to start hypervisor monitor for config %s: %s" % (args.config, e))

        nHypervisorMonitor.start()

        exit(0)
    except RuntimeError as excp:
        LOGGER.error("Runtime error while attempting to start monitoring for config %s under pidfile %s: %s\n" % (
            args.config, args.pidfile, excp))
        sys.exit(1)


if __name__ == '__main__':
    main()
