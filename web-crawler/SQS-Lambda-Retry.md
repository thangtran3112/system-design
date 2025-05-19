# SQS + Lambda with Exponential Backoff and DLQ

This project demonstrates how to implement **exponential backoff** for message retries in **Amazon SQS** with an **AWS Lambda function**, and safely handle failed messages using a **Dead Letter Queue (DLQ)**.

---

## 📐 Architecture Overview

```
+------------+         +--------------+         +-----------+
|            |         |              |         |           |
|  SQS Queue +-------->+  Lambda Func +-------->+  DLQ (SQS)|
|            |         |              |         |           |
+------------+         +--------------+         +-----------+
     |                        |
     |   Change visibility    |
     +------------------------+
         (Exponential Retry)
```

---

## ✅ Key Features

- Reads messages from SQS using Lambda trigger
- Tracks retry attempts using `ApproximateReceiveCount`
- Sets **visibility timeout dynamically** with exponential backoff
- Moves messages to **DLQ** after exceeding `maxReceiveCount`

---

## 🧠 Retry Logic (Lambda Handler)

```python
import boto3
import math

sqs = boto3.client('sqs')
QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123456789012/my-queue'

def lambda_handler(event, context):
    for record in event['Records']:
        message = record['body']
        receipt_handle = record['receiptHandle']
        receive_count = int(record['attributes']['ApproximateReceiveCount'])

        try:
            print(f"Processing message: {message} (attempt #{receive_count})")
            # Your logic here
            do_something(message)

        except Exception as e:
            print(f"Error: {e} - delaying retry")

            # Calculate exponential backoff
            base = 10
            backoff = min(base * (2 ** (receive_count - 1)), 43200)

            sqs.change_message_visibility(
                QueueUrl=QUEUE_URL,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=backoff
            )
```

---

## 📦 Behavior Summary

| Attempt | `ReceiveCount` | Visibility Timeout |
|---------|----------------|--------------------|
| 1       | 1              | 10 sec             |
| 2       | 2              | 20 sec             |
| 3       | 3              | 40 sec             |
| 4       | 4              | 80 sec             |
| 5       | 5              | 160 sec            |

Messages exceeding `maxReceiveCount` go to the DLQ automatically.

---

## ✅ Best Practices

- Monitor the DLQ and set up CloudWatch alarms.
- Add jitter to avoid thundering herd.
- Log error context for troubleshooting.
- Use Lambda Destinations for async post-processing if needed.

---

## 🛠️ To Do

- [ ] Add Terraform or CloudFormation templates
- [ ] Integrate monitoring and alerting
- [ ] Create tests for retry logic
