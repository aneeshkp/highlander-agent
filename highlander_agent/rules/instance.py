import json
import os
import sys
import time

from highlander_agent.common import log
from highlander_agent.common.constants import Constant
from highlander_agent.common.util import AgentConfigParser
from  highlander_agent.rpcclient.api import API

LOGGER = log.getLogger(Constant.LOGGER_MONITOR)
EVENT_LOGGER = log.getLogger(Constant.LOGGER_EVENT)


class Rules():

    @staticmethod
    def publish(routing_key, jsondata, instances=None, notifier=None):
        if notifier is not None:
            notifier.reinit(routing_key, '', '')
        if instances is not None:
            notifier.notify({"return_code": 501, "id": instances["id"], "message": jsondata})
        else:
            notifier.notify({"return_code": 501, "id": jsondata, "message": jsondata})

    @staticmethod
    def shutdown_monitoring(instanceid, jsondata, instances=None, notifier=None):
        cfg = AgentConfigParser()
        cfg.read(os.path.abspath(os.path.join(os.path.dirname(__file__), '../config.cfg')))
        cfg = cfg.as_dic()
        LOGGER.info(cfg)
        time.sleep(3)
        data1 = {
            "method": "stopmonitor",
            "arg": instanceid
        }
        msg = json.dumps(data1)
        try:
            api = API(cfg)
            EVENT_LOGGER.info("[*] EVENT calling RPC stopmonitor arg %s" % instanceid)
            response = api.call(msg)
            ###shutdown monitoring for this
            LOGGER.info("<<<<<<<<<<<<<<<<>>>>>>>>>>>>>> -instance is shutting down %r" % response)
            LOGGER.info("SHUTTING DOWN ALL MONITORING FOR THIS INSTANCE")
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()[:]
            LOGGER.error("Exception while trying toshutting down: %s, %s" % (exc_type, exc_tb.tb_lineno))
            EVENT_LOGGER.info("[1e][EVENT] EXCEPTION for Event stopmonitor arg %s" % instanceid)
            EVENT_LOGGER.error(
                "[2e][EVENT] Exception while executing shutdown_instance: %s, %s" % (exc_type, exc_tb.tb_lineno))

    @staticmethod
    def notify_instance(instanceid, jsonmessage, instances=None, notifier=None):
        # create notifier
        # send message
        if notifier == None:
            LOGGER.info("Cannot notify without hostname")
            return "Cannot notify without hostname"
        else:
            EVENT_LOGGER.info("[1][EVENT] calling RPC notify_instance   arg %s" % instanceid)
            EVENT_LOGGER.info("[2][EVENT] notify_instance jsonmessage  arg %s" % jsonmessage)
            notifier.notify(jsonmessage)
            LOGGER.info(">>>>>>>>>>>>>>>>>>>>>>instance is notifying  %r" % jsonmessage)

    @staticmethod
    def failover(instanceid, jsonmessage, instances=None, notifier=None):
        """
        :param jsondata:
        :param notifier:
        :return:

        - Needs to call configure for UFR failover (failover for UFR means turn on network interfaces)
        - Needs to make CLI call to axcons to FT failover, like so: /opt/ft/bin/axcons instance-000000d5 PVM set Preferred
          CoServer 2 From Ax1
        """
        LOGGER.info("%s ********#########-----> failing over" % instanceid)
        LOGGER.info("%s ********#########-----> failing over" % instanceid)
        LOGGER.info("%s ********#########-----> failing over" % instanceid)
        LOGGER.info("%s ********#########-----> failing over" % instanceid)

    @staticmethod
    def log_message(instanceid, jsonmessage, instances=None, notifier=None):
        LOGGER.info("!!!!!!!!!!!!!!!!LOG MESSAGE !!!!!!!!!!!!!")
        LOGGER.info("instance is logging  %r" % jsonmessage)
        EVENT_LOGGER.info("[1] EVENT log message executed  arg %s" % instanceid)

    @staticmethod
    def instance_start(instanceid, jsonmessage, instances=None, notifier=None):
        LOGGER.info("^^^^^^^^^^  START INSTANCE ^%^^^^^^^^^^")
        LOGGER.info("instance is logging  %r" % jsonmessage)

    @staticmethod
    def shutdown_instance(instanceid, jsonmessage, instances=None, notifier=None):
        """
        :param jsondata:
        :param notifier:
        :return:

        - Needs to call negotiator script for UFR shutdown (shutdown for UFR means turn off network interfaces)
        - Needs to make CLI call to axcons for FT shutdown, like so: /opt/ft/bin/axcons instance-000000d5 PVM set Preferred
          CoServer 1 From Ax2
        """
        cfg = AgentConfigParser()
        cfg.read(os.path.abspath(os.path.join(os.path.dirname(__file__), '../config.cfg')))
        cfg = cfg.as_dic()
        LOGGER.info(cfg)

        data = {
            "method": "shutdown_instance",
            "arg": instanceid
        }
        msg = json.dumps(data)
        try:
            api = API(cfg)
            EVENT_LOGGER.info("[1][EVENT] calling RPC shutdown _instance arg %s" % instanceid)
            EVENT_LOGGER.info("[2][EVENT] calling RPC shutdown _instance arg %s" % jsonmessage)
            response = api.call(msg)
            LOGGER.info("<<<<<<<<<<<<<<<<>>>>>>>>>>>>>> -instance is shutting down %r" % response)
            LOGGER.info("Executing scripts")
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()[:]
            LOGGER.error("Exception while executing scripts: %s, %s" % (exc_type, exc_tb.tb_lineno))
            EVENT_LOGGER.info("[1e][EVENT] EXCEPTION for Event shutdown_instance arg %s" % instanceid)
            EVENT_LOGGER.error(
                "[2e][EVENT] Exception while executing shutdown_instance: %s, %s" % (exc_type, exc_tb.tb_lineno))

    @staticmethod
    def wakeup_instance(instanceid, jsonmessage, instances=None, notifier=None):
        """
        :param jsondata:
        :param notifier:
        :return:

        - Needs to call negotiator script for UFR start (shutdown for UFR means turn on network interfaces)
        - Needs to make CLI call to axcons for FT start, like so: /opt/ft/bin/axcons instance-000000d5 PVM set Preferred
          CoServer 2 From Ax2
        """
        cfg = AgentConfigParser()
        cfg.read(os.path.abspath(os.path.join(os.path.dirname(__file__), '../config.cfg')))
        cfg = cfg.as_dic()
        LOGGER.info(cfg)

        data = {
            "method": "wakeup_instance",
            "arg": instanceid
        }
        msg = json.dumps(data)
        try:
            api = API(cfg)
            EVENT_LOGGER.info("[1][EVENT] calling RPC wakeup_instance arg %s" % instanceid)
            EVENT_LOGGER.info("[2][EVENT] calling RPC wakeup_instance arg %s" % jsonmessage)
            response = api.call(msg)
            LOGGER.info("<<<<<<<<<<<<<<<<>>>>>>>>>>>>>> -waking up other instance %r" % instanceid)
            LOGGER.info("Executing scripts")
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()[:]
            LOGGER.error("Exception while executing scripts: %s, %s" % (exc_type, exc_tb.tb_lineno))
            EVENT_LOGGER.info("[1e][EVENT]  EXCEPTION for Event wakeup_instance arg %s" % instanceid)
            EVENT_LOGGER.error(
                "[2e][EVENT] Exception while executing wakeup_instance: %s, %s" % (exc_type, exc_tb.tb_lineno))

    @staticmethod
    def configure(instanceid, jsonmessage, instances=None, notifier=None):
        """
        :param jsondata:
        :param notifier:
        :return:

        - Needs to use a particular virto serial socket for UFR (depends on which instance) to send a message
        to the guest to either turn on or turn off the guest's network interfaces
        - Not needed for FT
        """
        print "instance is configuring  %r" % jsonmessage
