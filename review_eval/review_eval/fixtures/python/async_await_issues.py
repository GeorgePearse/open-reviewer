# BAD: Multiple async/await anti-patterns
# Expected issues: await, asyncio.sleep, aiohttp, asyncio.run, create_task, async for
import asyncio
import time
import requests


# Anti-pattern 1: Missing await on coroutine call
async def fetch_data():
    """Simulate async data fetching."""
    await asyncio.sleep(0.1)
    return {"data": "example"}


async def process_data():
    """Missing await - returns coroutine object instead of data."""
    # This is wrong - missing await
    result = fetch_data()  # Returns <coroutine> not actual data
    return result


# Anti-pattern 2: Blocking time.sleep in async function
async def slow_operation():
    """Using blocking sleep in async function."""
    print("Starting operation...")
    # This blocks the entire event loop
    time.sleep(2)  # Should use asyncio.sleep(2)
    print("Operation complete")


# Anti-pattern 3: Blocking requests in async function
async def fetch_url(url: str):
    """Using blocking HTTP library in async function."""
    # This blocks the event loop - should use aiohttp
    response = requests.get(url)
    return response.json()


# Anti-pattern 4: asyncio.run() inside async context
async def nested_async_run():
    """Calling asyncio.run() from within async function."""
    async def inner_task():
        return "result"

    # This will raise RuntimeError: asyncio.run() cannot be called from a running event loop
    result = asyncio.run(inner_task())
    return result


# Anti-pattern 5: Fire-and-forget create_task without storing reference
async def fire_and_forget_tasks():
    """Creating tasks without storing references."""
    for i in range(5):
        # Task may be garbage collected before completion
        asyncio.create_task(slow_operation())  # No reference stored

    # Tasks might not complete if garbage collected


# Anti-pattern 6: Sync iteration over async iterator
async def process_items():
    """Using regular for loop with async generator."""
    async def async_generator():
        for i in range(3):
            await asyncio.sleep(0.1)
            yield f"item_{i}"

    items = []
    # Wrong - should use 'async for'
    for item in async_generator():  # This won't work as expected
        items.append(item)

    return items