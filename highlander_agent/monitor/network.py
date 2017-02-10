#!/usr/bin/env python


import argparse
import json
import os
import simplejson
import sys
import timeit

import eventlet
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
from highlander_agent.common.constants import Constant
from highlander_agent.common import log
from highlander_agent.common.util import AgentConfigParser
from highlander_agent.notifier import send
from highlander_agent.rules import instance
import string

LOGGER = log.getLogger(Constant.LOGGER_MONITOR)
FAILURE_LOGGER = log.getLogger(Constant.LOGGER_FAILURE)


class NetworkMonitor(HighlanderMonitorDaemon):
    def __init__(self, pidfile, instance_configuration_json, cfg):
        HighlanderMonitorDaemon.__init__(self, pidfile, instance_configuration_json)
        self._cfg = cfg

        #
        # Right now we are monitoring tap interfaces going down.  We may need to monitor
        # an actual physical interface (like FTCore does for KVM-FT).  If we need to
        # monitor an actual physical interface, we can always open the /etc/nova/kvmax.conf
        # file and extract it from there.  Of course, in that case, all network monitoring
        # processes create by a particular Highlander agent will be monitoring the same
        # interface, so perhaps then it would be advantageous to rearchitect this piece
        # of our monitoring.
        #
        # Anyhow, for now, find all the tap interfaces that belong to the instance and
        # store them in an array that we'll use when considering whether a target interface
        # went down or not. 
        #

        self._interfaces = []

        for instance in self._instances:
            if instance['id'] == self._instance_id_to_monitor:
                for port in instance['ports']:
                    LOGGER.warn(
                        "Monitoring interface %s for instance %s" % (port['name'], self._instance_id_to_monitor))
                    self._interfaces.append(port['name'])
                break

    def run(self):
        LOGGER.info("Running monitor for instance %s" % self._instance_id_to_monitor)
        if self._instance_configuration_json is None:
            LOGGER.warn("Instance %s configuration is missing during monitoring")
        else:
            self._monitor_network(self.on_event)

    def stop_processmonitor(self, instance_id):
        try:
            from highlander_agent.monitor.instance import InstanceMonitor
            pidfile = self._cfg[Constant.CONFIG_PIDFILE_SECTION]["instance_monitor"]
            pidfile = pidfile.replace("_INSTANCE", instance_id)
            monitorObject = InstanceMonitor(pidfile, None, self._cfg)
            pid = monitorObject.stop()
        except Exception, e:
            pass

    def _monitor_network(self, eventfun):
        from highlander_agent.monitor.lib.network import ip_monitor
        import thread
        try:

            LOGGER.info("Starting ip monitoring")
            ip = ip_monitor(self.on_network_event_callback)
            thread.start_new_thread(ip.run())
        except Exception, e:
            LOGGER.info("Error starting thread %s" % e)

    def on_event(self, event_type, event_message):
        if event_type == 'fail':
            self.on_fail_event()

    def on_network_event_callback(self, label, value, interface):
        LOGGER.info("[]LAbel ->%s" % label)
        LOGGER.info("[]value -->%s" % value)
        LOGGER.info("[]interface -->%s" % interface)
        label = str(label)
        label = label.strip(string.whitespace)
        value = str(value)
        value = value.strip(string.whitespace)

        """if label == "Link Up" and value == "False":
            if interface in self._interfaces:
                LOGGER.warn("Network is down identified for instance %s for port %s" % (
                    self._instance_id_to_monitor, interface))
        """
        # self.stop_processmonitor(self._instance_id_to_monitor)
        try:
            FAILURE_LOGGER.warn("[1] - Network down event for instance %s " % self._instance_id_to_monitor)
            self.on_event("fail", "Network failed")
            # sleep for 60 secs before trying to process again, this should die in the event of network failure because of stop_monitoring event
            time.sleep(300)
        except Exception, e:
            FAILURE_LOGGER.warn("[1] - Network down Exception for instance %s " % self._instance_id_to_monitor)
            LOGGER.error("[2]Exception while monitoring network %s: %s" % (self._instance_id_to_monitor, e))
            """else:
                LOGGER.info("Network down identified but not for instance %s" % self._instance_id_to_monitor)
            """

    def on_fail_event(self):
        # send notification to controller
        # run rules
        ## to do error handlers
        dashboard_json_method = []
        event_start_time = self.timestamp()
        index = 0
        if self._network_on_fail_event is not None:
            for entry in self._network_on_fail_event:
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
                    func = getattr(instance.Rules, method)

                    fun_start_time = self.timestamp()
                    if callable(func):
                        if method == "shutdown_monitoring":
                            stime = self.timestamp()
                            method_json = {"index": index, "method": method, "id": self._instance_id_to_monitor,
                                           "elapsed_time": stime, "time_started": stime,
                                           "time_completed": stime}
                            dashboard_json_method.append(method_json)
                            self.notify_node_js("ON_NETWORK_FAIL_EVENT", event_start_time, dashboard_json_method)

                        notifier = send.AgentNotifier(self._cfg, "AgentNotifier", hostname)
                        FAILURE_LOGGER.info("[2] - Network down event calling %s for instance %s " % (
                            method, self._instance_id_to_monitor))
                        start_time = timeit.default_timer()
                        func(arg["instance_id"], arg["message"], instanceObject, notifier)
                        elapsed_time = timeit.default_timer() - start_time
                        FAILURE_LOGGER.info("[3] - Completed Network down event calling %s for instance %s " % (
                            method, self._instance_id_to_monitor))
                        method_json = {"index": index, "method": method, "id": self._instance_id_to_monitor,
                                       "elapsed_time": elapsed_time, "time_started": fun_start_time,
                                       "time_completed": self.timestamp()}
                        dashboard_json_method.append(method_json)
                        FAILURE_LOGGER.info(method_json)
                    else:
                        FAILURE_LOGGER.error(
                            "[2] - Network down Exception calling %s for instance %s reason-NO_SUCH_METHOD" % (
                                method, self._instance_id_to_monitor))
                        return {"return_code": 500, "msg": "NoSuchMethod exception occurred %s" % method}
                except Exception, e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()[:]
                    FAILURE_LOGGER.error(
                        "[2e] - Network down Exception calling method for instance %s reason-NO_SUCH_METHOD" % (
                            self._instance_id_to_monitor))
                    FAILURE_LOGGER.error("[3e] -Exception details %s,%s" % (exc_type, exc_tb.tb_lineno))
                    LOGGER.error(
                        "Exception while trying to call method : %s, %s" % (exc_type, exc_tb.tb_lineno))
                    return {"return_code": 500, "msg": "NoSuchMethod exception occurred %r" % e}

            LOGGER.info(self._instance_on_fail_event)
            # notify nodejs
            self.notify_node_js("ON_FAIL_EVENT", event_start_time, dashboard_json_method)

    def delpid(self):
        pass

    def timestamp(self):
        now = time.time()
        localtime = time.localtime(now)
        milliseconds = '%03d' % int((now - int(now)) * 1000)
        return time.strftime('%Y-%m-%d:%H:%M:%S:', localtime) + milliseconds

    def notify_node_js(self, event_type, stime, jsonmethod):
        try:
            json_msg = {"type": "relay", "event_type": event_type, "event_start_time": stime, "event": "NETWORK",
                        "actions": jsonmethod}
            hostname = self._cfg["Host"]["hostname"]
            url = "ws://" + hostname + ":3001/events"
            FAILURE_LOGGER.info("Websocket connection to %s" % url)
            ws = websocket.create_connection(url)
            ws.send(json.dumps(json_msg))
            ws.close()
        except Exception, e:
            FAILURE_LOGGER.error("<<<<Exception occurred notifying node js [PROCESS] %r >>>>>" % e)


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
            nNetworkMonitor = NetworkMonitor(pidfile=args.pidfile,
                                             instance_configuration_json=simplejson.loads(args.config), cfg=cfg)
        except Exception, e:
            LOGGER.error("Exception while trying to start monitor for config %s: %s" % (args.config, e))

        nNetworkMonitor.start()

        exit(0)
    except RuntimeError as excp:
        LOGGER.error("Runtime error while attempting to start monitoring for config %s under pidfile %s: %s\n" % (
            args.config, args.pidfile, excp))
        sys.exit(1)


if __name__ == '__main__':
    main()
