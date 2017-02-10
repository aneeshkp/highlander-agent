import timeit
import uuid

import pika

from highlander_agent.common import log
from highlander_agent.common.constants import Constant

LOGGER = log.getLogger(Constant.LOGGER_RPC_SERVER)


class API(object):
    def __init__(self, cfg, agent_hostname=None):
        self._cfg = cfg
        self.credentials = pika.PlainCredentials(self._cfg["RabbitMQ"]["username"], self._cfg["RabbitMQ"]["secret"])
        if agent_hostname is None:
            self.routing_key = self._cfg["RPCServer"]["routing_key"]

        else:
            self.routing_key = str(self._cfg["RPCServer"]["routing_key_raw"]).replace("[]", agent_hostname)

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
            self.response = body

    def call(self, args, timeout=10):
        self.response = None
        count = 0
        self.corr_id = str(uuid.uuid4())

        self.channel.basic_publish(exchange=self.exchange,
                                   routing_key=self.routing_key,
                                   properties=pika.BasicProperties(
                                       reply_to=self.callback_queue,
                                       correlation_id=self.corr_id,
                                   ),
                                   body=args)

        start_time = timeit.default_timer()
        while self.response is None:
            self.connection.process_data_events(0)
            elapsed = timeit.default_timer() - start_time
            if self.response is None and float(elapsed) > float(timeout):
                self.response = 0
        return self.response
