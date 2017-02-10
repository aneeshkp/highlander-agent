import pika
import uuid
import json
import random
import time
import sys
import os
import simplejson
from decimal import Decimal
POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir, os.pardir, os.pardir))

if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'highlander_agent', '__init__.py')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from highlander_agent.common.util import AgentConfigParser


class AgentRpcClient(object):
    def __init__(self, cfg):
        self._cfg = cfg
        self.credentials = pika.PlainCredentials(self._cfg["RabbitMQ"]["username"], self._cfg["RabbitMQ"]["secret"])
        self.routing_key = self._cfg["RPCServer"]["routing_key"]
        self.exchange = self._cfg["RPCServer"]["exchange"]
        self.response = None
        self.corr_id = None
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(self._cfg["RabbitMQ"]["host"], int(self._cfg["RabbitMQ"]["port"]), '/',
                                      self.credentials))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(self.on_response, no_ack=True,
                                   queue=self.callback_queue)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            print method
            print props
            self.response = body

    def call(self, args):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(exchange=self.exchange,
                                   routing_key=self.routing_key,
                                   properties=pika.BasicProperties(
                                       reply_to=self.callback_queue,
                                       correlation_id=self.corr_id,
                                   ),
                                   body=args)
        while self.response is None:
            self.connection.process_data_events(0)
        return self.response


cfg = AgentConfigParser()
cfg.read(os.path.abspath(os.path.join(os.path.dirname(__file__), '../config.cfg')))
cfg = cfg.as_dic()

print sys.argv
if len(sys.argv) == 1:
    print "command line argument missing or not correct \n"
    print "> python client.py configure  \n\t\t Use this to configure"
    print "> python client.py stopmonitor  \n\t\t Use this to stop mointoring"
    print "> python client.py monitor \n\t\t use this option to start monitoring ."
    print "> python client.py execute \n\t\t use this option to execute negoitator script."
    print "> python client.py getconfig all \n\t\t use this option to get all config data."
    print "> python client.py heartbeat {hostname} \n\t\t use this option to get all config data."
    print "> python client.py getagentconfig  \n\t\t use this option to get application configuration."


    exit(1)
config_data = simplejson.loads(
    open(os.path.abspath(os.path.join(os.path.dirname(__file__), '../config/rpc_example.json'))).read())
agent_rpc_client = AgentRpcClient(cfg)
if sys.argv[1] == "heartbeat":
    if len(sys.argv) == 3:
        dta = {
            "method": "hypervisor_heartbeat",
            "arg": sys.argv[2]
        }
    msg = json.dumps(dta)
    from highlander_agent.rpcclient.api import API

    api = API(cfg, sys.argv[2])
   # response = api.call(msg)
    print "value"
    print cfg["Failover_Test"]["hypervisor_timeout"]
    
    response = api.call(msg,float(cfg["Failover_Test"]["hypervisor_timeout"]))
    print response

elif sys.argv[1] == "getconfig":
    if len(sys.argv) == 3:
        data = {
            "method": "getconfig",
            "arg": sys.argv[2]
        }
    else:
        data = {
            "method": "getconfig",
            "arg": "all"
        }
    msg = json.dumps(data)
    response = agent_rpc_client.call(msg)
    print response
elif sys.argv[1] == "getagentconfig":
    data = {
        "method": "getagentconfig",
        "arg": "all"
    }

    msg = json.dumps(data)
    response = agent_rpc_client.call(msg)
    print response
elif sys.argv[1] == "execute":
    data = {
        "method": "execute_negotiator_script",
        "arg": "1a1c8b46-bee3-4734-81f6-1a3b46581ca2"
    }
    msg = json.dumps(data)
    response = agent_rpc_client.call(msg)
    print response
elif sys.argv[1] == "configure":
    print"[.] METHOD - CONFIGURE"
    data = {
        "id": random.randint(1, 9999),
        "method": "configure",
        "arg": config_data
    }
    msg = json.dumps(data)
    response = agent_rpc_client.call(msg)
    print "sending to rpc %s" % msg
    print " [.] Got %r" % response
elif sys.argv[1] == "stopmonitor":
    print"[.] METHOD - STOP MONITOR"
    print "log file is in /tmp/higlander_monitoring_log.log"
    data1 = {
        "method": "stopmonitor",
        "arg": config_data["instance_to_monitor"]["id"]
    }
    msg = json.dumps(data1)
    response = agent_rpc_client.call(msg)
    print response
elif sys.argv[1] == "monitor":
    print"[.] METHOD - MONITOR"
    logfile = cfg["PidFile"]["monitor"]
    logfile = logfile.replace("_INSTANCE", config_data["instance_to_monitor"]["id"])
    print "pid file is in %s" % logfile
    print "log file is in /tmp/higlander_monitoring_log.log"

    stopmonitor = {
        "method": "stopmonitor",
        "arg": config_data["instance_to_monitor"]["id"]
    }
    msg = json.dumps(stopmonitor)
    response = agent_rpc_client.call(msg)
    print "first stopping monitor"
    print response
    print "start monitor"
    data2 = {
        "method": "monitor",
        "arg": config_data["instance_to_monitor"]["id"]
    }
    msg = json.dumps(data2)
    response = agent_rpc_client.call(msg)
    print response

else:
    print "command line argument missing or not correct \n"
    print "> python client.py configure  \n\t\t Use this to configure"
    print "> python client.py stopmonitor  \n\t\t Use this to stop mointoring"
    print "> python client.py monitor \n\t\t use this option to start monitoring ."
    print "> python client.py execute \n\t\t use this option to execute negoitator script."
    print "> python client.py getconfig all \n\t\t use this option to get all config data."
    print "> python client.py getagentconfig  \n\t\t use this option to get application configuration."

exit(0)

# agent_send_notification = AgentRpcClient("highlander.listener.hostname_4","highlander_listener_exchange_topic_4")

# r=agent_send_notification.call("Notify agent on the bridge")

# print r
