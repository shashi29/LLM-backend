import json
import pika

class RabbitMQClient:
    def __init__(self, host, queue, user, password):
        self.host = host
        self.queue = queue
        self.credentials = pika.PlainCredentials(user, password)
        
    def send_message(self, message, priority=0):
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.host,
                credentials=self.credentials
            )
        )
        channel = connection.channel()
        
        channel.queue_declare(queue=self.queue, durable=True)
        
        channel.basic_publish(
            exchange='',
            routing_key=self.queue,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # persistent delivery mode
                priority=priority
            )
        )
        
        connection.close()