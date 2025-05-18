URL Shortening with SHA-256 and Base62

This document explains how to shorten a long URL using: 1. SHA-256 for generating a unique, deterministic hash 2. Base62 encoding for a compact, URL-safe representation 3. A fixed 7-character Base62 code, giving over 3.5 trillion combinations

⸻

🌟 Goal

Given a long URL like:

https://example.com/a/really/long/path

We want to generate a 7-character Base62 short code:

abcD12X

    •	The code should be URL-safe
    •	Deterministic (same input, same output)
    •	Efficient to store and resolve

⸻

🔖 Step-by-Step Shortening Process

1. Input URL

Input: https://example.com/a/really/long/path

2. Hash URL Using SHA-256

Use SHA-256 to get a 64-character hexadecimal digest (256 bits total).

import hashlib
url = "https://example.com/a/really/long/path"
hash_digest = hashlib.sha256(url.encode()).hexdigest()
print(hash_digest)

Example output:

52912615f46993d83c4be528c26c276265b7086d2734cdd20c9f089420beac32

3. Extract First 44 Bits (≈11 Hex Characters)

Convert the first 11 hex digits to an integer:

int_val = int(hash_digest[:11], 16)

Example:

5661702322292

4. Convert Integer to Base62

Use a 62-character alphabet:

0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ

And convert using:

BASE62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def base62_encode(num):
if num == 0:
return BASE62[0]
result = []
while num > 0:
num, rem = divmod(num, 62)
result.append(BASE62[rem])
return ''.join(reversed(result))

short_code = base62_encode(int_val).rjust(7, '0')
print(short_code)

Example output:

0xA93eG

⸻

✅ Final Output

{
"original_url": "https://example.com/a/really/long/path",
"short_code": "0xA93eG"
}

You can map:

https://tiny.url/0xA93eG → https://example.com/a/really/long/path

⸻

📊 Why Use 7 Characters?
• Base62^7 = 62^7 = 3,521,614,606,208
• Over 3.5 trillion unique combinations
• Compact and collision-resistant for most URL shorteners

⸻

⚠️ Handling Collisions
• SHA-256 collisions are highly unlikely
• Still, store mappings in a database:
• short_code → original_url
• If collision occurs:
• Add salt
• Use next hash segment

⸻

🎓 Summary Table

Step Input/Output
SHA-256 Hex digest (64 chars)
Slice First 11 hex chars
Convert Base62 from int
Result 7-char URL-safe string

⸻

Let me know if you’d like a Flask or FastAPI implementation, or a Redis/PostgreSQL-backed version of this logic!
