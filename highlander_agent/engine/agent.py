"""
Abstract class
"""


class AgentService(object):


    def monitor(self, instanceid):
        """


        :param instance:
        :return:
        """
        raise NotImplementedError

    def stopmonitor(self, instanceid):
        """
        :param instance:
        :return:
        """
        raise NotImplementedError

    def status(self, instanceid):
        """

        :param instance:
        :return:
        """
        raise NotImplementedError

    def service_status(self, servicename ,key=None):
        """

        :param instance:
        :return:
        """
        raise NotImplementedError
    def start_listener(self):
        raise NotImplementedError

    def start_listener(self):
        raise NotImplementedError

