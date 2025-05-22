# redis_indexing.py

import redis
import time

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0)

# --- LIKE INDEX ---

def update_like_index(post_id: str, like_count: int):
    # Only update if like_count is a power of 2 (milestone)
    if like_count & (like_count - 1) == 0:
        r.zadd('like_index', {post_id: like_count})
        print(f"Updated like_index: {post_id} -> {like_count}")

def get_top_liked_posts(n=10):
    return r.zrevrange('like_index', 0, n - 1, withscores=True)

# --- CREATION INDEX ---

def add_post_creation(post_id: str):
    timestamp = int(time.time())
    r.zadd('created_index', {post_id: timestamp})
    print(f"Post added to created_index: {post_id} at {timestamp}")

def get_recent_posts(n=10):
    return r.zrevrange('created_index', 0, n - 1)

# --- POST STORAGE (optional) ---

def create_post(post_id: str, content: str, author: str):
    r.hset(f'post:{post_id}', mapping={'content': content, 'author': author})
    add_post_creation(post_id)

def get_post(post_id: str):
    return r.hgetall(f'post:{post_id}')

# Example usage:
if __name__ == '__main__':
    create_post('post123', 'Hello World', 'alice')
    update_like_index('post123', 1)
    update_like_index('post123', 2)
    print(get_top_liked_posts())
    print(get_recent_posts())
