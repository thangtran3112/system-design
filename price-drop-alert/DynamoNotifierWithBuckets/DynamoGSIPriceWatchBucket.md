
# 🔔 Price Drop Notification System with DynamoDB, Kafka, Redis

This service listens to product price updates and notifies users who are watching a product based on their alert price.

---

## 🏗️ Architecture Overview

```
+---------------------------+
| Kafka Topic: price_updates|
| (productId, newPrice)     |
+---------------------------+
           |
           v
+-------------------------------+
| PriceDropNotifierService      |
| - Consumes Kafka updates      |
| - Reads from Redis/DynamoDB   |
| - Publishes notification req  |
+-------------------------------+
           |
           v
+-------------------------------+
| Kafka Topic: user_notifications |
+-------------------------------+
           |
           v
+-------------------------------+
| Notification Service          |
| - Reads messages              |
| - Sends email/SMS/Push        |
+-------------------------------+
```

---

## 🗃️ DynamoDB Table Design

### Table: `PriceWatch`

| Attribute          | Role             |
|--------------------|------------------|
| `productId`        | Partition Key    |
| `userId`           | Sort Key         |
| `priceWatchValue`  | Non-key attribute|

### GSI: `PriceIndex`

| GSI Attribute      | Role             |
|--------------------|------------------|
| `productId`        | Partition Key    |
| `priceWatchValue`  | Sort Key         |

---

## 🧠 Price Bucket Optimization for Hot Products

For products with frequent updates, repeated range scans can cause excessive load. Instead, bucket watch prices into ranges:

### Table: `PriceWatchBucketed`

| Attribute        | Role                        |
|------------------|-----------------------------|
| `productId`      | Partition Key               |
| `priceBucket`    | Sort Key (e.g., price // 10)|
| `userId`         | Attribute                   |

### Query:
```python
bucket = int(new_price) // 10
response = dynamodb.query(
    TableName='PriceWatchBucketed',
    KeyConditionExpression='productId = :pid AND priceBucket >= :bkt',
    ExpressionAttributeValues={
        ':pid': {'S': 'P123'},
        ':bkt': {'N': str(bucket)}
    }
)
```

Reduces cardinality and improves hot product scalability.

---

## 🔁 Redis Caching

- Cache result of user list per bucket:
  - `redis.setex(f"watch:P123:{bucket}", 300, json.dumps(user_ids))`
- Check Redis first, fallback to DynamoDB.
- Use TTL to avoid staleness.

---

## 🔗 Kafka Topics

### Input: `price_updates`

```json
{
  "productId": "P123",
  "newPrice": 79.99
}
```

### Output: `user_notifications`

```json
{
  "userId": "U456",
  "productId": "P123",
  "newPrice": 79.99
}
```

---

## ✅ Best Practices

- Use Redis for caching hot product watchers
- Bucket by price to minimize range scan load
- Use GSI on `priceWatchValue` only for moderately updated products
- Monitor read/write units and hot partitions
