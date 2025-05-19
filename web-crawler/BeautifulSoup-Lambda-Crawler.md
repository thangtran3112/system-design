# 🕸️ AWS Lambda HTML Text Crawler with SQS + S3

This project sets up a **serverless crawler** that:

- Receives **URLs from SQS**
- Fetches and parses HTML content with **BeautifulSoup**
- Stores clean text into **Amazon S3** using a domain-based prefix

---

## 📐 Architecture

```
[SQS Queue] ---> [Lambda Function] ---> [S3 Bucket]
   |                 |                      |
   |                 |                      +-- s3://my-bucket/domain.com/yyyy-mm-dd/uuid.txt
   |                 |
   |                 +-- BeautifulSoup HTML cleaner
```

---

## ✅ Features

- Uses `requests` to fetch webpage content
- Uses `BeautifulSoup + lxml` to clean text
- S3 prefix layout: `domain-name/yyyy-mm-dd/uuid.txt`
- Handles failures with basic exception logging
- Metadata includes original `source-url`

---

## 🧑‍💻 Lambda Function Code (Python)

```python
import boto3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime
import uuid

s3 = boto3.client('s3')

BUCKET_NAME = "my-crawled-pages-bucket"

def extract_text(html):
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)

def extract_domain(url):
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "")

def lambda_handler(event, context):
    for record in event['Records']:
        url = record['body'].strip()
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()

            text = extract_text(resp.text)
            domain = extract_domain(url)
            date_prefix = datetime.utcnow().strftime("%Y-%m-%d")
            object_key = f"{domain}/{date_prefix}/{uuid.uuid4()}.txt"

            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=object_key,
                Body=text.encode("utf-8"),
                Metadata={"source-url": url}
            )

            print(f"[✓] Stored: s3://{BUCKET_NAME}/{object_key}")

        except Exception as e:
            print(f"[!] Failed to fetch {url}: {e}")
```

---

## 🔧 Deployment Steps

1. **Create an IAM Role** for Lambda with:
   - `sqs:ReceiveMessage`
   - `s3:PutObject`
   - `logs:*`

2. **Create Lambda function** using the code above (Python 3.9+)

3. **Attach your SQS queue** as an event source trigger

4. **Ensure your S3 bucket exists**

---

## 📁 S3 Object Structure

```
s3://my-crawled-pages-bucket/
├── example.com/
│   ├── 2024-05-20/
│   │   ├── <uuid>.txt
```

---

## 🚀 Improvements

- Add CloudWatch alerts for failed fetches
- Add Dead Letter Queue (DLQ) for SQS
- Add retry/backoff with delay queues
- Support content-type filtering
- Use Lambda Layers or container image for dependencies

---

Let me know if you need a Terraform or CloudFormation deployment guide!
