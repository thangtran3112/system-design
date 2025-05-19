# 🌐 Understanding Domain, URL, and robots.txt for Web Crawling

This guide explains the differences between **domain** and **URL**, and how the `robots.txt` file is used to guide web crawler behavior.

---

## 🔹 1. Domain vs URL

### ✅ Domain
The **name of a website** (e.g., `example.com`). It's a part of a full URL and represents the root address.

### ✅ URL (Uniform Resource Locator)
The **complete web address** that points to a specific resource (including domain, path, and query).

#### Example:
```
URL: https://www.example.com/products?page=2
|__ Protocol: https://
    |__ Domain: www.example.com
                 |__ Path: /products
                      |__ Query: ?page=2
```

---

## 🤖 2. What is `robots.txt`?

### ✅ Definition:
A `robots.txt` file is a publicly accessible text file placed at the **root of a domain** to **guide web crawlers** on what parts of the site they are allowed to access or must avoid.

### ✅ Location:
```
https://example.com/robots.txt
```

### ✅ Purpose:
- Controls crawler access to URLs
- Reduces server load
- Prevents indexing of sensitive or irrelevant areas

---

## 📄 3. Example `robots.txt` Files

### 🛑 Block Specific Paths
```txt
User-agent: *
Disallow: /admin/
Disallow: /private/
```

### ✅ Allow Only a Section
```txt
User-agent: *
Disallow: /
Allow: /public/
```

### 🤖 Specific Bot Rules
```txt
User-agent: Googlebot
Disallow: /sandbox/

User-agent: Bingbot
Allow: /
```

### 🕰️ Set Crawl Delay
```txt
User-agent: *
Crawl-delay: 10
```

> This instructs bots to wait 10 seconds between requests.

> ⚠️ `Crawl-delay` is not universally supported (Google ignores it, Bing honors it)

---

## 🧪 4. How a Crawler Uses `robots.txt`

1. Receive URL: `https://example.com/page1.html`
2. Extract domain: `example.com`
3. Fetch: `https://example.com/robots.txt`
4. Parse and check if `/page1.html` is allowed

### Example (Python):
```python
import urllib.robotparser

rp = urllib.robotparser.RobotFileParser()
rp.set_url("https://example.com/robots.txt")
rp.read()

rp.can_fetch("*", "https://example.com/admin/")  # Returns False
```

---

## ✅ Summary

| Concept      | Description                          |
|--------------|--------------------------------------|
| **Domain**   | Root name of a website               |
| **URL**      | Full resource address                |
| **robots.txt** | File that guides crawler behavior  |
| **Crawl-delay** | Optional delay between requests    |

---

## 🚀 Pro Tips

- Always check `robots.txt` before crawling.
- Respect `Disallow` and `Crawl-delay` for ethical scraping.
- Combine with request throttling and retries.
