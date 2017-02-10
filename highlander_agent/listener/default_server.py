import pika
import simplejson
import signal
from highlander_agent.listener.server import AgentListener
from daemon import HighlanderListenerDaemon
from highlander_agent.common.constants import Constant
from highlander_agent.common import log
from highlander_agent.notifier import send
from highlander_agent.rules import instance
import sys

LOGGER = log.getLogger(Constant.LOGGER_LISTENER)


class DefaultListenerServer(HighlanderListenerDaemon, AgentListener):
    def __init__(self, cfg):
        HighlanderListenerDaemon.__init__(self, cfg[Constant.CONFIG_PIDFILE_SECTION]["listener"])
        AgentListener.__init__(self, cfg, cfg["Host"]["hostname"])
        self.cfg = cfg

    def run(self):
        self.start_listiner()

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
        LOGGER.info('Received message # %s from %s: %s',
                    basic_deliver.delivery_tag, properties.app_id, body)




        LOGGER.info('Received message # %s from %s: %s',
                    basic_deliver.delivery_tag, properties.app_id, body)
        try:
            self._execute_onmessage(body)
            response = "listener processed the request"
            # get function name and args from payload

        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()[:]
            LOGGER.error("[] Exception while trying process message : %s, %s" % (exc_type, exc_tb.tb_lineno))
        self.acknowledge_message(basic_deliver.delivery_tag)

    def _execute_onmessage(self, body):

        LOGGER.info(body)
        if "rule" in body:
            message = simplejson.loads(body)
            method = message["rule"]["method"]
            LOGGER.info(method)
            arg = message['rule']['arg']
            LOGGER.info('arg')
            LOGGER.info(arg)
            LOGGER.info(arg["instance_id"])
            hostname = None

            # LOGGER.info("hostname %s" % hostname)
            LOGGER.info("method name %s" % method)
            try:
                rules = instance.Rules()
                func = getattr(instance.Rules, method)
                if callable(func):
                    LOGGER.info("instance_id %s" % arg["instance_id"])
                    LOGGER.info("message %s" % arg["message"])
                    LOGGER.info("hostname %s" % hostname)
                    # notifier = send.AgentNotifier(self._cfg, "AgentNotifier", hostname)
                    func(arg["instance_id"], arg["message"],None, None)
                    return {"return_code": 200, "msg": "Executed []method:%s" %method}
                else:
                    LOGGER.error("Not callable")
                    return {"return_code": 500, "msg": "NoSuchMethod exception occurred"}
            except Exception, e:
                exc_type, exc_obj, exc_tb = sys.exc_info()[:]
                LOGGER.error(
                    "Exception while trying to start monitor for config: %s, %s" % (exc_type, exc_tb.tb_lineno))
                return {"return_code": 500, "msg": "NoSuchMethod exception occurred %r" % e}
        else:
            LOGGER.info("$$$$$$$$$$$$$$$$$$$$$$$$")
            LOGGER.info("Logging message received")
            LOGGER.info(body)
            return {"return_code": 200, "msg": "Logging message received"}
            # return {"return_code": 200, "msg": "Logged"}
