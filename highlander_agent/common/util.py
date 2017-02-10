INSTANCE_STATUS_FAIL = "*.instance.status.fail"
INSTANCE_STATUS_RUNNING = "*.instance.status.running"
INSTANCE_STATUS_STOPPED = "*.instance.status.stopped"
INSTANCE_STATUS_OKAY = "*.instance.status.okay"

_instance_config = []

import ConfigParser
import socket


class InstanceConfigUtil(object):
    @staticmethod
    def prase_instanceconfig(configjs):
        monitor_types = None
        instance_id_to_monitor = None
        instance_id_to_monitor = None
        instance_on_fail_event = None
        instance_on_ok_event = None
        network_on_fail_event = None
        network_on_ok_event = None
        instances = None
        hypervisor_to_monitor = None

        try:
            monitor_types = configjs["monitor_types"]
            instance_id_to_monitor = configjs["instance_to_monitor"]["id"]
            try:
                instance_on_fail_event = configjs["instance_to_monitor"]["instance"]["on_fail_event"]
            except KeyError:
                pass
            try:
                instance_on_ok_event = configjs["instance_to_monitor"]["instance"]["on_ok_event"]
            except KeyError:
                pass
            try:
                network_on_fail_event = configjs["instance_to_monitor"]["network"]["on_fail_event"]
            except KeyError:
                pass
            try:
                network_on_ok_event = configjs["instance_to_monitor"]["network"]["on_ok_event"]
            except KeyError:
                pass

            try:
                hypervisor_to_monitor = configjs["instance_to_monitor"]["hypervisor"]
            except KeyError:
                pass
            instances = configjs["instances"]
        except KeyError:
            monitor_types = None

        return monitor_types, instance_id_to_monitor, instance_on_fail_event, instance_on_ok_event, network_on_fail_event, network_on_ok_event, instances, hypervisor_to_monitor


class AgentConfigParser(ConfigParser.ConfigParser):
    def as_dic(self):
        self.sanitize()
        d = dict(self._sections)
        for k in d:
            d[k] = dict(self._defaults, **d[k])
            d[k].pop('__name__', None)

        return d

    def sanitize(self):
        for option, value in self.items("Host"):
            self.replace("Host", option, value.replace("_gethostname_", socket.gethostname()))
            break
        hostname = self.get("Host", "hostname")
        sections = self.sections()
        for section in sections:
            try:
                for option, value in self.items(section):
                    if "[HOSTNAME]" in value:
                        self.replace(section, option, value.replace("[HOSTNAME]", hostname))
            except ValueError:
                pass

    def replace(self, section, option, newstring):
        self.set(section, option, newstring)
