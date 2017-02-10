#!/usr/bin/env python


import argparse
import json
import os
import simplejson
import subprocess
import sys
import timeit
from threading import Thread

import eventlet
import psutil as ps
import websocket

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
from highlander_agent.common.util import AgentConfigParser
from highlander_agent.common.constants import Constant
from highlander_agent.common import log
from highlander_agent.notifier import send
from highlander_agent.rules import instance

LOGGER = log.getLogger(Constant.LOGGER_MONITOR)
FAILURE_LOGGER = log.getLogger(Constant.LOGGER_FAILURE)


class InstanceMonitor(HighlanderMonitorDaemon):
    def __init__(self, pidfile, instance_configuration_json=None, cfg=None):
        HighlanderMonitorDaemon.__init__(self, pidfile, instance_configuration_json)
        self._cfg = cfg
        self._instance_name = None

        if instance_configuration_json is not None:
            for instance in self._instances:
                if instance['id'] == self._instance_id_to_monitor:
                    LOGGER.warn("Attempting to find QEMU process with instance name '%s' for instance %s" % (
                        instance['name'], self._instance_id_to_monitor))
                    self._instance_name = instance['name']
                    break

            self._target = []

            procs = ps.pids()

            for proc in procs:
                p = ps.Process(proc)

                if len(p.cmdline()) > 2 and p.cmdline()[1] == '-name' and p.cmdline()[2] == self._instance_name:
                    LOGGER.warn("Monitoring instance %s as process: %s" % (self._instance_id_to_monitor, p.cmdline()))
                    self._target.append(p)
                    break

    def on_term(self, proc):
        FAILURE_LOGGER.warn("[1] - Instance fail event for  %s " % self._instance_id_to_monitor)
        self.on_event("fail", "fail event occurred")

    """
    RUN
    """

    def run(self):
        LOGGER.info("Running monitor for instance %s" % self._instance_id_to_monitor)
        if self._instance_configuration_json is None:
            LOGGER.warn("Instance %s configuration is missing during monitoring")
        else:
            try:
                # start a new thread to process on ok
                if self._instance_on_ok_event is not None:
                    ok_event = Thread(target=self._on_ok_event_monitoring)
                    try:
                        ok_event.start()
                    except (KeyboardInterrupt, SystemExit):
                        LOGGER.error("[] ******On OK EVENT for instance STOPPED **********[]")
                LOGGER.info("Starting process monitoring for on_fail_event")
                while True:
                    LOGGER.info("Monitoring for instance %s failure" % self._instance_id_to_monitor)
                    gone, alive = ps.wait_procs(self._target, 1, callback=self.on_term)
                    time.sleep(1)
            except Exception, e:
                FAILURE_LOGGER.warn("[1] - Instance (fail) Exception  for  %s " % self._instance_id_to_monitor)
                LOGGER.error("EXCEPTION--> monitoring instance failed %r" % e)

    """
    Actual Monitoring process
    """

    def _on_ok_event_monitoring(self):
        myinstance = None
        for instance in self._instances:
            if instance["id"] == self._instance_id_to_monitor:
                myinstance = instance
                break
        if myinstance["resiliency_strategy"] != "ufr":
            LOGGER.info(
                "No need to monitor KVM-FT instance %s for primary/secondary status" % self._instance_id_to_monitor)
            exit(0)
        for instance in self._instances:
            if instance["id"] != myinstance["id"] and instance["resiliency_strategy"] == "ft" and instance[
                "resiliency_side"] == myinstance["resiliency_side"]:
                ftinstance = instance
                break
        if ftinstance is None:
            LOGGER.error(
                "Unable to find affinitized FT instance for UFR instance %s primary/secondary status monitoring" % self._instance_id_to_monitor)
            exit(0)
        while True:
            LOGGER.info("Checking if this side is alive and active for UFR instance %s" % myinstance["id"])

            myscript = ["/opt/ft/bin/axcons", ftinstance["name"], "show",
                        "ax%s.scp" % ftinstance["resiliency_side"], "device", "status"]
            out, err = subprocess.Popen(myscript, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

            try:
                lines = out.split("\n")
                line = None
                if ftinstance["resiliency_side"] == 1:
                    line = lines[9]
                else:
                    line = lines[10]

                line = [item for item in line.split(" ") if item != ""]

                LOGGER.info("Line: %s" % line)

                if line[3] == "Active":
                    self._on_ok_event()
                    exit(0)
            except Exception, e:
                LOGGER.error("Exception while monitoring primary/secondary status of %s: %r" % (
                    self._instance_id_to_monitor, e))
            time.sleep(1)

    """
    ON OK EVENT
    """

    def _on_ok_event(self):
        LOGGER.info("Monitoring ON OK EVENT: %s" % self._instance_on_ok_event)
        dashboard_json_method = []
        event_start_time = self.timestamp()
        index = 0
        if self._instance_on_ok_event is not None:
            try:
                for instanceObject in self._instances:
                    if instanceObject["id"] == self._instance_id_to_monitor:
                        myinstance = instanceObject
                        break
                for entry in self._instance_on_ok_event:
                    method = entry["rule"]["method"]
                    arg = entry["rule"]["arg"]
                    func = getattr(instance.Rules, method)
                    if callable(func):
                        notifier = send.AgentNotifier(self._cfg, "AgentNotifier", myinstance["host_name"])
                        start_time = timeit.default_timer()
                        fun_start_time = self.timestamp()
                        func(arg["instance_id"], arg["message"], myinstance, notifier)
                        elapsed_time = timeit.default_timer() - start_time
                        method_json = {"index": index, "method": method, "id": self._instance_id_to_monitor,
                                       "elapsed_time": elapsed_time, "time_started": fun_start_time,
                                       "time_completed": self.timestamp()}
                        dashboard_json_method.append(method_json)
                        FAILURE_LOGGER.info(method_json)
                        # All done, exit
                    else:
                        LOGGER.error("Unable to send primary/secondary status %s message to %s for instance %s" % (
                            method, myinstance["hostname"], myinstance["id"]))
            except Exception, e:
                LOGGER.error("NO SUCH METHOD EXCEPTION %r" % e)
            # notify nodejs
            self.notify_node_js("ON_OK_EVENT", event_start_time, dashboard_json_method)

    def _monitor_process(self, eventfun):
        failpath = str(self._cfg["Failover_Test"]["path"]).replace("[INSTANCE]", self._instance_id_to_monitor)
        LOGGER.info("FAIL PATH %s" % failpath)
        while True:
            time.sleep(0.1)

            #             if os.path.exists(failpath):
            #                 LOGGER.info(" failure detected for %s" % self._instance_id_to_monitor)
            #                 try:
            #                     eventfun("fail", "fail event occured")
            #                     time.sleep(30)#sleep for 30 secounds on failure , the agent will eventually shutdown
            #                 except Exception, e:
            #                     LOGGER.error("Exception while monitoring instance %s: %s" % (self._instance_id_to_monitor, e))
            # else:
            # LOGGER.info("No instance failure detected for %s" % self._instance_id_to_monitor)

    """
    ON EVENT
    """

    def on_event(self, event_type, event_message):
        if event_type == 'fail':
            try:
                self.on_fail_event()
            except Exception, e:
                exc_type, exc_obj, exc_tb = sys.exc_info()[:]
                LOGGER.error(
                    "Exception while trying to start monitor for config: %s, %s" % (exc_type, exc_tb.tb_lineno))

    """
    ON FAIL EVENT
    """

    def on_fail_event(self):
        # send notification to controller
        # run rules
        ## to do error handlers
        dashboard_json_method = []
        event_start_time = self.timestamp()
        index = 0
        if self._instance_on_fail_event is not None:
            for entry in self._instance_on_fail_event:
                index += 1
                method = entry["rule"]["method"]
                arg = entry["rule"]["arg"]
                for item in self._instances:
                    if item["id"] == arg["instance_id"]:
                        instanceObject = item
                        break
                    else:
                        instanceObject = None
                if instanceObject == None:
                    hostname = None
                else:
                    hostname = instanceObject["host_name"]
                try:

                    rules = instance.Rules()
                    start_time = timeit.default_timer()
                    func = getattr(instance.Rules, method)
                    if callable(func):
                        if method == "shutdown_monitoring":
                            stime = self.timestamp()
                            method_json = {"index": index, "method": method, "id": self._instance_id_to_monitor,
                                           "elapsed_time": stime, "time_started": stime,
                                           "time_completed": stime}
                            dashboard_json_method.append(method_json)
                            self.notify_node_js("ON_FAIL_EVENT", event_start_time, dashboard_json_method)

                        notifier = send.AgentNotifier(self._cfg, "AgentNotifier", hostname)
                        FAILURE_LOGGER.info(
                            "[2] - Calling action %s on fail for  %s " % (method, self._instance_id_to_monitor))
                        fun_start_time = self.timestamp()
                        func(arg["instance_id"], arg["message"], instanceObject, notifier)
                        FAILURE_LOGGER.info(
                            "[3] -Complete Calling action %s on fail for  %s " % (method, self._instance_id_to_monitor))
                        elapsed_time = timeit.default_timer() - start_time
                        method_json = {"index": index, "method": method, "id": self._instance_id_to_monitor,
                                       "elapsed_time": elapsed_time, "time_started": fun_start_time,
                                       "time_completed": self.timestamp()}
                        FAILURE_LOGGER.info(method_json)
                        dashboard_json_method.append(method_json)
                    else:
                        FAILURE_LOGGER.warn(
                            "[2] - failed to call  %s on fail for  %s  reason NO_SUCH_METHOD " % (
                                method, self._instance_id_to_monitor))
                        return {"return_code": 500, "msg": "NoSuchMethod exception occurred %s" % method}
                except Exception, e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()[:]
                    LOGGER.error(
                        "Exception while trying to start monitor for config: %s, %s" % (exc_type, exc_tb.tb_lineno))
                    FAILURE_LOGGER.warn(
                        "[2e] - failed to call  method on fail for  %s  reason NO_SUCH_METHOD " % (
                            self._instance_id_to_monitor))
                    FAILURE_LOGGER.warn("[3e] -Exception details %s,%s" % (exc_type, exc_tb.tb_lineno))
                    return {"return_code": 500, "msg": "NoSuchMethod exception occurred %r" % e}

            LOGGER.info(self._instance_on_fail_event)

            # notify nodejs
            self.notify_node_js("ON_INSTANCE_FAIL_EVENT", event_start_time, dashboard_json_method)

    """
    Notify dashboard
    """

    def notify_node_js(self, event_type, stime, jsonmethod):
        try:
            json_msg = {"type": "relay", "event_type": event_type, "event_start_time": stime, "event": "PROCESS",
                        "actions": jsonmethod}
            hostname = self._cfg["Host"]["hostname"]
            url = "ws://" + hostname + ":3001/events"
            FAILURE_LOGGER.info("Websocket connection to %s" % url)
            ws = websocket.create_connection(url)
            ws.send(json.dumps(json_msg))
            ws.close()
        except Exception, e:
            LOGGER.error("<<<<Exception occurred notifying node js [PROCESS] %r >>>>>" % e)

    def delpid(self):
        pass

    def timestamp(self):
        now = time.time()
        localtime = time.localtime(now)
        milliseconds = '%03d' % int((now - int(now)) * 1000)
        return time.strftime('%Y-%m-%d:%H:%M:%S:', localtime) + milliseconds


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
            instanceMonitor = InstanceMonitor(pidfile=args.pidfile,
                                              instance_configuration_json=simplejson.loads(args.config), cfg=cfg)
        except Exception, e:
            LOGGER.error("Exception while trying to start monitor for config %s: %s" % (args.config, e))

        instanceMonitor.start()

        exit(0)
    except RuntimeError as excp:
        LOGGER.error("Runtime error while attempting to start monitoring for config %s under pidfile %s: %s\n" % (
            args.config, args.pidfile, excp))
        sys.exit(1)


if __name__ == '__main__':
    main()
