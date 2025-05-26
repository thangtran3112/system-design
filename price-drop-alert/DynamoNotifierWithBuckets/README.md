
# 🔔 Price Drop Notification System using DynamoDB, Redis, Kafka

This system listens to product price updates and notifies users who have registered interest in a product if its price drops to or below their desired threshold.

---

## 🏗️ Architecture Overview

```
+-----------------------------+
| Kafka: price_updates        |
| (productId, newPrice)       |
+-----------------------------+
           |
           v
+-------------------------------+
| PriceDropNotifierService      |
| - Consumes Kafka updates      |
| - Checks Redis cache          |
| - Queries DynamoDB if needed  |
| - Publishes notification req  |
+-------------------------------+
           |
           v
+-------------------------------+
| Kafka: user_notifications     |
+-------------------------------+
           |
           v
+-------------------------------+
| Notification Service          |
| - Consumes user_notifications |
| - Sends email/SMS/push        |
+-------------------------------+
```

---

## 🗃️ DynamoDB Modeling Options

### Option 1: Simple Model (No Buckets)

#### Table: `PriceWatch`

| Attribute         | Role             |
|-------------------|------------------|
| `productId`       | Partition Key    |
| `userId`          | Sort Key         |
| `priceWatchValue` | Attribute        |

#### Use Case:
- Simple to manage and query
- Efficient for moderate product update frequency

#### GSI: `PriceIndex`
- Partition Key: `productId`
- Sort Key: `priceWatchValue`

#### Query:
```python
dynamodb.query(
    TableName='PriceWatch',
    IndexName='PriceIndex',
    KeyConditionExpression='productId = :pid AND priceWatchValue >= :price',
    ExpressionAttributeValues={
        ':pid': {'S': 'P123'},
        ':price': {'N': '79.99'}
    }
)
```

---

### Option 2: Bucketed Composite Key Model

#### Table: `PriceWatchBucketed`

| Attribute       | Role                                |
|----------------|-------------------------------------|
| `productId`     | Partition Key                       |
| `bucket_userId` | Composite Sort Key (e.g. 8#user123) |
| `priceBucket`   | Used for query filtering            |
| `userId`        | Optional copy for readability       |

#### Why use this?
- Better for high frequency price updates
- Avoids large GSI fan-outs
- Prevents hot partitions

#### Composite Key:
```python
bucket = int(priceWatchValue) // 10
sort_key = f"{bucket}#{userId}"
```

#### Query:
```python
dynamodb.query(
    TableName='PriceWatchBucketed',
    KeyConditionExpression='productId = :pid AND begins_with(bucket_userId, :bkt)',
    ExpressionAttributeValues={
        ':pid': {'S': 'P123'},
        ':bkt': {'S': '8#'}
    }
)
```

> To query `priceBucket >= N`, scan partition and filter in memory or pre-bucket with a range of keys.

---

## 🧠 Redis Optimization for Hot Products

- Used to cache watcher lists by product + bucket:
```python
redis.setex("watch:P123:8", 300, json.dumps([user1, user2]))
```

- Use Redis `GET` before DynamoDB `query`
- Reduces pressure on DynamoDB for hot products

---

## 🔗 Kafka Integration

### Input Topic: `price_updates`
```json
{
  "productId": "P123",
  "newPrice": 79.99
}
```

### Output Topic: `user_notifications`
```json
{
  "userId": "user123",
  "productId": "P123",
  "newPrice": 79.99
}
```

---

## ✅ Suggestions

| Use Case                      | Recommendation                          |
|-------------------------------|------------------------------------------|
| Low-frequency updates         | Use simple model with GSI                |
| High-frequency, many watchers| Use bucketed + Redis cache               |
| High read volume              | Use Redis cache with TTL (~5 min)        |
| Cold product or cache miss    | Fall back to DynamoDB                    |
| Multi-region setup            | Use DAX or global tables for DynamoDB    |

---

## 📁 Files

- `README.md` (this file)
