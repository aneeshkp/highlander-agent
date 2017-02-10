import json
import os
import simplejson
import subprocess
import sys
import time
import timeit
from signal import SIGTERM
from threading import Thread

import websocket

from highlander_agent.common import log
from highlander_agent.common.constants import Constant
from highlander_agent.common.util import InstanceConfigUtil
from highlander_agent.engine.agent import AgentService
from highlander_agent.listener.default_server import DefaultListenerServer
from highlander_agent.monitor.hypervisor import HypervisorMonitor
from highlander_agent.monitor.instance import InstanceMonitor
from highlander_agent.monitor.network import NetworkMonitor
from highlander_agent.notifier.send import AgentNotifier

LOGGER = log.getLogger(Constant.LOGGER_RPC_SERVER)


class DefaultAgentService(AgentService):
    """
    dictionary are not immutable so danger danger
    """

    def __init__(self, cfg):
        self._cfg = cfg
        self._instanceconfigurations = {}
        self._monitored_instance = {}
        self._monitored_network = {}
        self._monitored_hypervisor = {}
        self._failed_instances = {}
        self._hostname = self._cfg["Host"]["hostname"]
        self._controllerNotifier = AgentNotifier(cfg, Constant.CONFIG_CONTROLLER_NOTIFIER_SECTION)
        self._controllerNotifier.reinit(None, '', '')

    def configure(self, instanceid, configjson):
        try:
            monitor_types, instance_id_to_monitor, instance_on_fail_event, instance_on_ok_event, network_on_fail_event, network_on_ok_event, instances, hypervisor_to_monitor = InstanceConfigUtil.prase_instanceconfig(
                configjson)
            if monitor_types is None:
                return {"return_code": 500, "msg": "Failed to configure instance %s" % instanceid}
            self._instanceconfigurations[instance_id_to_monitor] = configjson
            return {"return_code": 200, "msg": "Successfully configured instance %s" % instanceid}
        except Exception, e:
            return {"return_code": 500, "msg": "Exception occured while configuring instance %s %r" % (instanceid, e)}

    def getconfig(self, instanceid="all"):
        if instanceid == "all":
            return self._instanceconfigurations
        elif instanceid in self._instanceconfigurations:
            return self._instanceconfigurations[instanceid]
        else:
            return {}

    def get_instance_configurations(self):
        return self._instanceconfigurations

    def get_instance_monitored(self):
        return self._monitored_instance

    """
    Stop Monitoring
    """

    def execute_negotiator_script_asycn(self, instanceid, state="on"):
        porcessthread = Thread(target=self.execute_negotiator_script, args=(instanceid, state))
        porcessthread.start()
        LOGGER.info("Running execute script in a thread for %s" % instanceid)

    def execute_negotiator_script(self, instanceid, state="on"):
        target_instance = None
        LOGGER.info(self._instanceconfigurations)
        dashboard_json_method = []
        event_start_time = self.timestamp()
        if instanceid in self._instanceconfigurations:
            LOGGER.info("Sa$$execute_negotiator_script")
            try:
                monitor_types, instance_id_to_monitor, instance_on_fail_event, instance_on_ok_event, network_on_fail_event, network_on_ok_event, instances, hypervisor_to_monitor = InstanceConfigUtil.prase_instanceconfig(
                    self._instanceconfigurations.get(instanceid))
                for item in instances:
                    if item["id"] == instanceid:
                        target_instance = item
                        break
                    else:
                        target_instance = None
                if target_instance is None:
                    LOGGER.info("Can not  execute_negotiator_script")
                    return {"return_code": 500,
                            "msg": "Could not find instance details.%s" % instanceid}
                else:
                    LOGGER.info("$ABC$execute_negotiator_script")
                    name = target_instance["name"]
                    if not all(resiliency in target_instance for resiliency in
                               ("resiliency_strategy", "resiliency_side")):
                        return {"return_code": 500,
                                "msg": "Could not identify script to execute since strategy key is missing "}
                    resiliency_strategy = target_instance["resiliency_strategy"]
                    resiliency_side = target_instance["resiliency_side"]
                    script_1 = None
                    """
                    Buuild scripts based on ufr or ft
                    """
                    if resiliency_strategy == "ufr":
                        script_1 = None
                    elif resiliency_strategy == "ft":
                        if resiliency_side == 2 and state == "on":
                            script_1 = "/opt/ft/bin/axcons %s PVM set Preferred CoServer 2 From Ax2" % name
                        elif resiliency_side == 1 and state == "off":
                            script_1 = "/opt/ft/bin/axcons %s PVM set Preferred CoServer 1 From Ax2" % name
                        else:
                            LOGGER.error(
                                "Could not identify script for %s with resiliency_strategy %s and  resiliency_side %s " % (
                                    name, resiliency_strategy, resiliency_side))
                            return {"return_code": 500,
                                    "msg": "[X]Could not identify script for %s with strategy %s and side %s " % (
                                        name, resiliency_strategy, resiliency_side)}
                    else:
                        LOGGER.error("Could not identify script for %s with strategy %s and side %s " % (
                            name, resiliency_strategy, resiliency_side))
                        return {"return_code": 500,
                                "msg": "Could not identify script for %s with strategy %s and side %s " % (
                                    name, resiliency_strategy, resiliency_side)}

                    """
                    Loop through ports and execute scripts
                    """
                    if resiliency_strategy == "ufr":
                        script_1 = "negotiator-host -e %s_%s.sh %s" % (target_instance["id"], state, name)
                    LOGGER.info(script_1)
                    try:
                        start_time = timeit.default_timer()
                        fun_start_time = self.timestamp()
                        os.system(script_1)
                        elapsed_time = timeit.default_timer() - start_time
                        method_json = {"index": 0, "method": "SCRIPT", "id": instanceid,
                                       "elapsed_time": elapsed_time, "time_started": fun_start_time,
                                       "time_completed": self.timestamp()}
                        dashboard_json_method.append(method_json)
                        self.notify_node_js("ON_WAKEUP_SHUTDOWN_SCRIPT_" + state, event_start_time,
                                            dashboard_json_method)
                        # subprocess.call([script_1], shell=True)
                    except OSError, o:
                        LOGGER.error("Exception executing shell script %r" % o)
                        return {"return_code": 500, "msg": "Script failed to execute for %s" % instanceid}

                    LOGGER.info("%s script executed successfully" % script_1)
                    return {"return_code": 200, "msg": "Scripts executed for %s" % instanceid}

            except Exception, e:
                LOGGER.error("Exception occurred while execute negotiator script %s %r" % (instanceid, e))
                return {"return_code": 500,
                        "msg": "Exception occurred while execute negotiator script %s %r" % (instanceid, e)}

    """
    stop monitoring
    """

    def stopmonitor(self, instanceid):
        return self._stopallmonitor(instanceid)

    """
    stop all monitoring
    """

    def _stopallmonitor(self, instanceid):
        monitor_types = ["INSTANCE", "NETWORK", "HYPERVISOR"]
        try:

            for monitor_type in monitor_types:
                monitorObject = self._getMonitorObjectType(instanceid, monitor_type)
                try:
                    pid = monitorObject.stop()
                except SystemExit, a:
                    time.sleep(5)
                if pid is not None or self.status(instanceid, monitor_type):
                    msg = {"return_code": 500,
                           "msg": "Monitoring failed to stop for %s  for  instance %s" % (monitor_type, instanceid)}
                else:
                    if monitor_type == "HYPERVISOR":
                        if instanceid in self._monitored_hypervisor:
                            self._monitored_hypervisor.pop(instanceid)
                    elif monitor_type == "INSTANCE":
                        if instanceid in self._monitored_instance:
                            self._monitored_instance.pop(instanceid)
                    elif monitor_type == "NETWORK":
                        if instanceid in self._monitored_network:
                            self._monitored_network.pop(instanceid)

            self._controllerNotifier.notify({"return_code": 200,
                                             "msg": "Stop monitoring service succeeded for %s for instance %s" % (
                                                 monitor_types, instanceid), "event": "STOP_MONITOR", "id": instanceid})
            return {"return_code": 200,
                    "msg": "Stop monitoring service succeeded for %s for instance %s" % (monitor_types, instanceid)}
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()[:]
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            return {"return_code": 500,
                    "msg": "Stop monitoring service failed for %s for instance %r: (%s, %s, %s)" % (
                        monitor_type, e, exc_type, fname, exc_tb.tb_lineno)}

    """
    Start monitoring
    """

    def monitor(self, instanceid, restart=None):
        instance_configuration_json = None

        if instanceid in self._instanceconfigurations:
            instance_configuration_json = self._instanceconfigurations[instanceid]
        if instance_configuration_json is not None:
            self._monitor_types, self._instance_id_to_monitor, self._instance_on_fail_event, self._instance_on_ok_event, self._network_on_fail_event, self._network_on_ok_event, self._instances, self._hypervisor_to_monitor = InstanceConfigUtil.prase_instanceconfig(
                instance_configuration_json)
        else:
            return {"return_code": 500,
                    "msg": "No configuration file found" % instanceid}

        return_instance = {"return_code": 500, "msg": "Not running"}
        return_network = {"return_code": 500, "msg": "Not running"}
        return_hypervisor = {"return_code": 500, "msg": "Not running"}
        return_array = {"return_code": 500, "msg": "Not running"}

        return_code = 200
        instance_monitor_state = "Not running"
        network_monitor_state = "Not running"
        hypervisor_monitor_state = "Not running"
        LOGGER.info("Starting monitoring")
        if "instance" in self._monitor_types:
            LOGGER.info("Starting instance monitoring")
            return_instance = self._monitor_monitor(instanceid, None, "INSTANCE", None)

        if return_instance["return_code"] == 200:
            instance_monitor_state = "Running"

        if "network" in self._monitor_types:
            LOGGER.info("Starting network monitoring")
            return_network = self._monitor_monitor(instanceid, None, "NETWORK", None)

        if return_network["return_code"] == 200:
            network_monitor_state = "Running"

        if "hypervisor" in self._monitor_types and self._hypervisor_to_monitor:
            LOGGER.info("Starting hypervisor monitoring")
            return_hypervisor = self._monitor_monitor(instanceid, self._hypervisor_to_monitor["hostname"], "HYPERVISOR",
                                                      None)
        if return_hypervisor["return_code"] == 200:
            hypervisor_monitor_state = "Runnning"

        if return_instance["return_code"] != 200 or return_network["return_code"] != 200 or return_hypervisor[
            "return_code"] != 200:
            return_code = 500

        return {"return_code": return_code,
                "msg": "following monitors are in running/not running state Instance=%s ,Network=%s,Hypervisor=%s" % (
                    instance_monitor_state, network_monitor_state, hypervisor_monitor_state),
                "result": "[ %s,%s,%s]" % (return_instance, return_network, return_hypervisor)}

    """
    Actuall monitoring process
    """

    def _monitor_monitor(self, instanceid, hypervisor, monitor_type, restart=None):
        msg = "msg"
        LOGGER.info("monitor type %s" % monitor_type)
        if monitor_type == "INSTANCE":
            if instanceid in self._monitored_instance:
                monitored_instance = self._monitored_instance[instanceid]
            else:
                monitored_instance = None
        elif monitor_type == "NETWORK":
            if instanceid in self._monitored_network:
                monitored_instance = self._monitored_network[instanceid]
            else:
                monitored_instance = None
        elif monitor_type == "HYPERVISOR":
            if instanceid in self._monitored_hypervisor:
                monitored_instance = self._monitored_hypervisor[instanceid]
            else:
                monitored_instance = None

        if instanceid in self._instanceconfigurations:
            monitor_config = self._instanceconfigurations[instanceid]
        else:
            monitor_config = None

        # kill the daemon and start again
        pidfile = self._getpidfile(instanceid, monitor_type)
        monitor_file = self._getfilelocation(monitor_type)
        LOGGER.info("pid file")
        LOGGER.info(pidfile)
        LOGGER.info("monitor  file")
        LOGGER.info(monitor_file)

        # instanceMonitor = InstanceMonitor(pidfile, monitor_config, self._cfg)
        if monitor_config:
            if monitored_instance:
                if restart:
                    try:
                        # instanceMonitor.restart()
                        pass
                    except SystemExit, a:
                        time.sleep(5)
                    pid = self.status(instanceid, monitor_type)
                    if pid:
                        return {"return_code": 200,
                                "msg": "Monitoring started successfully for %s for instance %s" % (
                                    monitor_type, instanceid)}
                    else:
                        return {"return_code": 500,
                                "msg": "Failed to start monitoring service for %s instance %s" % (
                                    monitor_type, instanceid)}
                elif self.status(instanceid, monitor_type):
                    return {"return_code": 200,
                            "msg": "Monitoring service is already running for %s instance %s" % (
                                monitor_type, instanceid)}
                else:
                    try:
                        subprocess.call(["python", os.path.abspath(
                            os.path.join(os.path.dirname(__file__), monitor_file)), "-c",
                                         simplejson.dumps(monitor_config), "-p", pidfile])
                    except SystemExit, s:
                        time.sleep(5)
                        LOGGER.info("Exit occured %d (%s)\n" % (s.errno, s.strerror))
                    pid = self.status(instanceid, monitor_type)

                    if pid:
                        self._monitored_instance[instanceid] = pid
                        return {"return_code": 200,
                                "msg": "Monitoring started successfully for %s instance %s" % (
                                    monitor_type, instanceid)}
                    else:
                        return {"return_code": 500,
                                "msg": "Failed to start monitoring service for %s instance %s" % (
                                    monitor_type, instanceid)}
            else:
                # spawn monitored service
                try:
                    msg = subprocess.call(
                        ["python", os.path.abspath(os.path.join(os.path.dirname(__file__), monitor_file)),
                         "-c", simplejson.dumps(monitor_config), "-p", pidfile])
                except SystemExit, a:
                    LOGGER.info("Exit captured %r" % a)
                    time.sleep(5)

                pid = self.status(instanceid, monitor_type)
                LOGGER.info("PID")
                LOGGER.info(pid)
                if pid:
                    if monitor_type == "HYPERVISOR":
                        self._monitored_hypervisor[instanceid] = pid
                    elif monitor_type == "INSTANCE":
                        self._monitored_instance[instanceid] = pid
                    elif monitor_type == "NETWORK":
                        self._monitored_network[instanceid] = pid
                    return {"return_code": 200,
                            "msg": "Monitoring started successfully for %s instance %s" % (monitor_type, instanceid)}
                else:
                    return {"return_code": 500,
                            "msg": "Failed to start monitoring service for %s instance %s" % (monitor_type, instanceid)}
        else:
            return {"return_code": 500,
                    "msg": "Instance %s failed to configure -- notify monitoring agent %s " % (
                        monitor_type, instanceid)}

    """
    Check the status of monitor agent (check for process id)
    """

    def status(self, instanceid, monitor_type=None, notify=False):
        pidfile = None
        pid = None

        # Get the pid from the pidfile
        pidfile = self._getpidfile(instanceid, monitor_type)
        try:
            pf = file(pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError, i:
            LOGGER.error("status check failed: %d (%s)\n" % (i.errno, i.strerror))
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n" % pidfile

        return pid

    """
    Return service status by service name
    """

    def service_status(self, servicename, key=None):
        pass

    """
    kill Process byt pidfile
    """

    def get_pid(self, instanceid, monitor_type):
        # Get the pid from the pidfile
        pidfile = self._getpidfile(instanceid, monitor_type)
        try:
            pf = file(pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        if not pid:
            return None
        else:
            return pid

    def _kill_process(self, pidfile, pid):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n" % pidfile
            return message  # not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
                if os.path.exists(pidfile):
                    os.remove(pidfile)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(pidfile):
                    os.remove(pidfile)
            else:
                print str(err)
                sys.exit(1)

    def start_listener(self):
        l = DefaultListenerServer(self._cfg)
        l.start()

    def stop_listener(self):
        l = DefaultListenerServer(self._cfg)
        l.stop()

    def _getpidfile(self, instanceid, monitor_type):
        pidfile = None
        if monitor_type == "INSTANCE":
            pidfile = self._cfg[Constant.CONFIG_PIDFILE_SECTION]["instance_monitor"]
            pidfile = pidfile.replace("_INSTANCE", instanceid)
        elif monitor_type == "NETWORK":
            pidfile = self._cfg[Constant.CONFIG_PIDFILE_SECTION]["network_monitor"]
            pidfile = pidfile.replace("_INSTANCE", instanceid)
        elif monitor_type == "HYPERVISOR":
            pidfile = self._cfg[Constant.CONFIG_PIDFILE_SECTION]["hypervisor_monitor"]
            pidfile = pidfile.replace("_INSTANCE", instanceid)

        return pidfile

    def _getMonitorObjectType(self, instanceid, monitor_type):
        """
        :param instanceid:
        :param monitor_type:
        :return:
        """

        pidfile = self._getpidfile(instanceid, monitor_type)

        if instanceid in self._instanceconfigurations:
            monitor_config = self._instanceconfigurations[instanceid]
        else:
            monitor_config = None
        LOGGER.info("file to del %s" % pidfile)

        if monitor_type == "INSTANCE":
            return InstanceMonitor(pidfile, monitor_config, self._cfg)
        elif monitor_type == "NETWORK":
            return NetworkMonitor(pidfile, monitor_config, self._cfg)
        else:
            return HypervisorMonitor(pidfile, monitor_config, self._cfg)

    def _getfilelocation(self, monitor_type):
        if monitor_type == "INSTANCE":
            return '../monitor/instance.py'
        elif monitor_type == "NETWORK":
            return '../monitor/network.py'
        elif monitor_type == "HYPERVISOR":
            return '../monitor/hypervisor.py'

    def notify_node_js(self, event_type, stime, jsonmethod):
        try:
            json_msg = {"type": "relay", "event_type": event_type, "event_start_time": stime, "event": "ENGINE",
                        "actions": jsonmethod}

            url = "ws://" + self._hostname + ":3001/events"
            LOGGER.info("Websocket connection to %s" % url)
            ws = websocket.create_connection(url)
            ws.send(json.dumps(json_msg))
            ws.close()
        except Exception, e:
            LOGGER.error("<<<<Exception occurred notifying node js [PROCESS] %r >>>>>" % e)

    def timestamp(self):
        now = time.time()
        localtime = time.localtime(now)
        milliseconds = '%03d' % int((now - int(now)) * 1000)
        return time.strftime('%Y-%m-%d:%H:%M:%S:', localtime) + milliseconds
