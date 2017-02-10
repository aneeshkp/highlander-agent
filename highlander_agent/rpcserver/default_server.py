import simplejson

import pika

from highlander_agent.common import log
from highlander_agent.common.constants import Constant
from highlander_agent.engine.default_agent import DefaultAgentService
from highlander_agent.rpcserver.daemon import HighlanderRPCDaemon
from highlander_agent.rpcserver.endpoint import RPCEndpoint
from highlander_agent.rpcserver.server import RPCServer

LOGGER = log.getLogger(Constant.LOGGER_RPC_SERVER)
EVENT_LOGGER = log.getLogger(Constant.LOGGER_EVENT)


class DefaultRPCServer(HighlanderRPCDaemon, RPCServer):
    def __init__(self, cfg, log_name=None):
        HighlanderRPCDaemon.__init__(self, cfg[Constant.CONFIG_PIDFILE_SECTION]["server"])
        RPCServer.__init__(self, cfg)
        self.cfg = cfg

        self._defaultagentservice = DefaultAgentService(cfg)

    def run(self):
        self.start_rpc()

    def getconfig(self, instanceid):
        return self._defaultagentservice.getconfig()

    def getagentconfig(self, dummy=None):
        return self.cfg

    def configure(self, configjson):
        try:
            instanceid = configjson["instance_to_monitor"]["id"]
            return self._defaultagentservice.configure(instanceid, configjson)
        except Exception, e:
            return "Error configuring instance %r" % e

    def stopmonitor(self, instanceid):
        print 'stopping instance for instance %s' % instanceid
        try:
            return self._defaultagentservice.stopmonitor(instanceid)
        except Exception, e:
            return "Exception while stopping monitor %r" % e

    def shutdown_instance(self, instance_id):
        EVENT_LOGGER.info("[1][RPC] starting shutdown_instance arg %s" % instance_id)
        return self._defaultagentservice.execute_negotiator_script(instance_id, "off")

    def wakeup_instance(self, instance_id):
        EVENT_LOGGER.info("[1][RPC] starting wakeup_instance arg %s" % instance_id)
        return self._defaultagentservice.execute_negotiator_script(instance_id, "on")

    def check_monitor_service_status(self, pid_loc):
        pid = None
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
        try:
            return self._defaultagentservice.monitor(instanceid)

        except Exception, e:
            return "Error Monitoring instance %r" % e

    def status(self, instanceid):
        return "instance status is"

    def hypervisor_heartbeat(self, hostname):
        return 1

    def on_message(self, unused_channel, basic_deliver, properties, body):
        """Invoked by pika when a message is delivered from RabbitMQ. The
        channel is passed for your convenience. The basic_deliver object that
        is passed in carries the exchange, routing key, delivery tag and
        a redelivered flag for the message. The properties passed in is an
        instance of BasicProperties with the message properties and the body
        is the message that was sent.

        :param pika.channel.Channel unused_channel: The channel object
        :param pika.Spec.Basic.Deliver: basic_deliver method
        :param pika.Spec.BasicProperties: properties
        :param str|unicode body: The message body

        """
        response = {"return_code": 200, "msg": "Message received"}
        bad_data = False
        data = None

        EVENT_LOGGER.info('[1][RPC]Received message # %s from %s: %s',
                          basic_deliver.delivery_tag, properties.app_id, body)
        # response = "Got the message, ok from server" + body
        try:
            data = simplejson.loads(body)
        except Exception, e:
            EVENT_LOGGER.info("[1e][RPC]Exception onMessage arg %s" % e)
            LOGGER.error("Non-JSON message received, ignoring")
            bad_data = True
            response = {"return_code": 400, "msg": "Non-JSON message received, ignoring"}

        if not bad_data:
            try:
                method = data["method"]
                LOGGER.info("method is %s", method)
                arg = data["arg"]
                LOGGER.info("argument is %s", arg)
                response = {"return_code": 500, "msg": "Method not found"}
                try:
                    rpcservice = RPCEndpoint(None, None)
                    func = getattr(self, method)
                    if callable(func):
                        EVENT_LOGGER.info("[2][RPC] calling method %s" % method)
                        response = func(arg)
                    else:
                        EVENT_LOGGER.info("[2][RPC] Exception onMessage -MO+_SUCH_METHOD")
                        response = {"return_code": 500, "msg": "NoSuchMethod exception occurred "}
                except Exception, e:
                    LOGGER.info("exception occurred calling method %s" % e)
                    EVENT_LOGGER.info("[2e][RPC] Exception onMessage -MO+_SUCH_METHOD %s" % e)
            except Exception, e:
                LOGGER.error("Improperly formatted message received, ignoring")
                EVENT_LOGGER.info("[2e][RPC] Exception onMessage Improperly formatted messag")
                bad_data = True
                response = {"return_code": 400, "msg": "Improperly formatted message received, ignoring"}

        # get function name and args from payload
        LOGGER.info("reply to %s", properties.reply_to)
        unused_channel.basic_publish(exchange="",
                                     routing_key=properties.reply_to,
                                     properties=pika.BasicProperties(correlation_id=properties.correlation_id),
                                     body=simplejson.dumps(response))

        LOGGER.info('Received message # %s from %s: %s',
                    basic_deliver.delivery_tag, properties.app_id, body)
        self.acknowledge_message(basic_deliver.delivery_tag)
