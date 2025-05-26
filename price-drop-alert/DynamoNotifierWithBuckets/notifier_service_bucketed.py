
import json
import redis
import boto3
from kafka import KafkaConsumer, KafkaProducer

# Config
DYNAMO_TABLE = 'PriceWatchBucketed'
REDIS_HOST = 'localhost'
KAFKA_BROKER = 'localhost:9092'
NOTIF_TOPIC = 'user_notifications'
UPDATE_TOPIC = 'price_updates'

# Setup
dynamodb = boto3.client('dynamodb')
rds = redis.Redis(host=REDIS_HOST, decode_responses=True)
consumer = KafkaConsumer(
    UPDATE_TOPIC,
    bootstrap_servers=[KAFKA_BROKER],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)
producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda m: json.dumps(m).encode('utf-8')
)

def get_user_ids(product_id, new_price):
    bucket = int(new_price) // 10
    cache_key = f"watch:{product_id}:{bucket}"
    cached = rds.get(cache_key)
    if cached:
        return json.loads(cached)

    resp = dynamodb.query(
        TableName=DYNAMO_TABLE,
        KeyConditionExpression='productId = :pid AND priceBucket >= :bkt',
        ExpressionAttributeValues={
            ':pid': {'S': product_id},
            ':bkt': {'N': str(bucket)}
        },
        ProjectionExpression='userId'
    )
    user_ids = [item['userId']['S'] for item in resp.get('Items', [])]
    rds.setex(cache_key, 300, json.dumps(user_ids))
    return user_ids

# Main loop
for msg in consumer:
    product_id = msg.value['productId']
    new_price = float(msg.value['newPrice'])
    user_ids = get_user_ids(product_id, new_price)

    for uid in user_ids:
        notif = {
            'userId': uid,
            'productId': product_id,
            'newPrice': new_price
        }
        producer.send(NOTIF_TOPIC, value=notif)
        print(f"Notification sent: {notif}")
