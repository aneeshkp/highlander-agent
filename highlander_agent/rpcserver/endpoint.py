"""
Configure will store configuration
start monitoring will start monitoring thread
update configure will update configure.
"""

import json


class RPCEndpoint(object):
    def __init__(self, defaultagentservice, notifier):
        self._defaultagentservice = defaultagentservice
        self._notifier = notifier

    def configure(self, configjson):
        return "Sure will configure for you...hello its me"
        parsed_json = json.loads(configjson)
        instance_to_monitor = parsed_json["instances_to_monitor"]
        print "INSTANCES TO MONITOR: %s" % instance_to_monitor
        on_fail_event = instance_to_monitor["on_fail_event"]
        print "ON_FAIL: %s" % on_fail_event
        instances = parsed_json["instances"]
        print "INSTANCES: %s" % instances
        self._defaultagentservice.configure(configjson)

    def stopmonitor(self, instanceid):
        print 'stop instance for instance %s' % instanceid
        return "OK stopped instance from monitoring  .. hello its me"
    def execute_nego_script(self,instance_id):
        pass


    def check_monitor_service_status(self,pid_loc):
        pid=None
        try:
           pf = file(pid_loc, 'r')
           pid = int(pf.read().strip())
           pf.close()
        except IOError:
            pid = None

        if pid:
            return True
        else:
            return False

    def monitor(self, instanceid):
        """
        return pid
        :param instanceid:
        :return:
        """
        print 'start monitoring for instance %s' % instanceid


        return "OK started to monitor instance  .. hello its me"


    def status(self, instanceid):
        return "instance status is ok .. hello its me"
