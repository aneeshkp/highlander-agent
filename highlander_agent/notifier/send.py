import sys
import uuid

import pika

from highlander_agent.common import log
from highlander_agent.common.constants import Constant

LOGGER = log.getLogger(Constant.LOGGER_LISTENER)

from highlander_agent.common.constants import Constant
import simplejson


class AgentNotifier(object):
    def __init__(self, cfg, queue_section_name, hostname=None):
        """Setup the example publisher object, passing in the URL we will use
        to connect to RabbitMQ.

        :param str amqp_url: The URL for connecting to RabbitMQ

        """

        self._rabbit_cfg = cfg[Constant.CONFIG_RABBIT_SECTION]
        self._queue_cfg = cfg[queue_section_name]
        self._connection = None
        self.response = None
        self.corr_id = None
        self._consumer_tag = None
        if hostname is None:
            self.ROUTING_KEY = self._queue_cfg['notifier_routing_key']
        else:
            self.ROUTING_KEY = self._queue_cfg['notifier_routing_key'].replace("*", hostname)

        self.EXCHANGE = self._queue_cfg['exchange']
        self.EXCHANGE_TYPE = "topic"
        self.QUEUE = self._queue_cfg["notifier_queue"]
        LOGGER.info("**************NOTIFIER **********************")
        LOGGER.info("ROUTING_KEY %s" % self.ROUTING_KEY)
        LOGGER.info("EXCHANGE %s" % self.EXCHANGE)
        LOGGER.info("EXCHANGE_TYPE %s" % self.EXCHANGE_TYPE)
        LOGGER.info("QUEUE %s" % self.QUEUE)
        LOGGER.info("************************************")

    def reinit(self, routing_key=None, exchange=None, queue=None):
        if exchange is not None:
            self.EXCHANGE = exchange
        if routing_key is not None:
            self.ROUTING_KEY = routing_key
        if queue is not None:
            self.QUEUE = queue

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            print method
            print props
            self.response = body

    def _connect(self):
        self.credentials = pika.PlainCredentials(self._rabbit_cfg['username'], self._rabbit_cfg['secret'])
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(self._rabbit_cfg['host'], int(self._rabbit_cfg['port']), '/', self.credentials))
        self._channel = self.connection.channel()
        result = self._channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue

        self._channel.basic_consume(self.on_response, no_ack=True,
                                    queue=self.callback_queue)

    def _disconnect(self):
        self._channel.close()
        # self._connection.close()

    def notify(self, message):
        self._connect()
        self.response = None
        self.corr_id = str(uuid.uuid4())
        try:
            LOGGER.error(message)
            data = simplejson.dumps(message)
            LOGGER.error(data)
            properties = pika.BasicProperties(correlation_id=self.corr_id, app_id=self.ROUTING_KEY,
                                              content_type='application/json')
            self._channel.basic_publish(exchange=self.EXCHANGE,
                                        routing_key=self.ROUTING_KEY,
                                        properties=properties,
                                        body=data)
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()[:]
            LOGGER.error("Exception while sending notification: %s, %s" % (exc_type, exc_tb.tb_lineno))
        """while self.response is None:
            self.connection.process_data_events()
        return self.response"""
        self._disconnect()


"""def main():
    cfg = {}
    cfg["listener_routing_key"] = "highlander.listener.hostname_2"
    cfg["listener_exchange"] = "highlander_listener_exchange_topic_2"
    cfg["username"] = "guest"
    cfg["secret"] = "guest"
    cfg["host"] = "localhost"
    cfg["port"] = 5672

    agent = AgentNotifier(cfg)

    agent.notify("hi Hello there.. you got to so aomethind")
    # agent.stop()

"""

"""
python send.py instance.fail "hello world"
python send.py instance.suspended "hello world"
"""
