import pika
import json
from typing import Dict, Callable, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RabbitMQClient:
    def __init__(self, host: str, queue: str, user: str, password: str, max_priority: int = 10, virtual_host: str = '/'):
        self.host = host
        self.queue = queue
        self.user = user
        self.password = password
        self.max_priority = max_priority
        self.virtual_host = virtual_host  # Added virtual_host parameter with default '/'
        self.connection = None
        self.channel = None

    def _get_connection(self):
        if not self.connection or self.connection.is_closed:
            credentials = pika.PlainCredentials(self.user, self.password)
            # Added virtual_host to connection parameters
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=self.host, 
                credentials=credentials,
                virtual_host=self.virtual_host,
                heartbeat=600,
                blocked_connection_timeout=600
            ))
            self.channel = self.connection.channel()
        return self.connection, self.channel

    def _declare_queue(self):
        _, channel = self._get_connection()
        channel.queue_declare(
            queue=self.queue, 
            durable=True,
            arguments={'x-max-priority': self.max_priority}
        )

    def send_message(self, message: Dict, priority: int = 0):
        try:
            _, channel = self._get_connection()
            self._declare_queue()
            priority = max(0, min(priority, self.max_priority))
                         
            channel.basic_publish(
                exchange='',
                routing_key=self.queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    priority=priority
                )
            )
            logger.info(f"Sent message with priority {priority}: {message}")
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    def start_consumer(self, callback: Callable):
        def internal_callback(ch, method, properties, body):
            message = json.loads(body)
            priority = properties.priority or 0
            logger.info(f"Received message with priority {priority}: {message}")
            callback(message)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        try:
            _, channel = self._get_connection()
            self._declare_queue()
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=self.queue, on_message_callback=internal_callback)
            logger.info('Waiting for messages. To exit press CTRL+C')
            channel.start_consuming()
        except Exception as e:
            logger.error(f"Error in consumer: {e}")

    def check_health(self):
        try:
            self._get_connection()
            self._declare_queue()
            return True
        except Exception as e:
            logger.error(f"RabbitMQ health check failed: {e}")
            return False

    def close_connection(self):
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                self.connection = None
                self.channel = None
                logger.info("Connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")