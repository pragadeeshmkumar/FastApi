from fastapi import FastAPI, HTTPException
from collections import deque

app = FastAPI()

class LRUCache:
    def __init__(self, capacity: int):
        self.cache = {}
        self.capacity = capacity
        self.order = deque()

    def get(self, key: str):
        if key not in self.cache:
            return None
        self.order.remove(key)
        self.order.appendleft(key)
        return self.cache[key]

    def put(self, key: str, value: str):
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.capacity:
            oldest_key = self.order.pop()
            del self.cache[oldest_key]
        self.cache[key] = value
        self.order.appendleft(key)

cache = LRUCache(capacity=3)

@app.post("/api/04")
def put_item(key: str, value: str):
    cache.put(key, value)
    return {"message": "Item added to cache"}

@app.get("/api/05")
def get_item(key: str):
    value = cache.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"key": key, "value": value}
