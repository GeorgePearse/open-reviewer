# BAD: Common async/await anti-patterns
# Expected issues: await, asyncio.sleep, aiohttp, event loop, fire-and-forget, async iterator
import asyncio
import time
import requests


async def fetch_data_missing_await():
    """Missing await on coroutine call."""
    # This returns a coroutine object, not the actual result
    result = asyncio.sleep(1)  # Missing await
    return result


async def blocking_time_sleep():
    """Using blocking time.sleep in async function."""
    print("Starting task...")
    # This blocks the entire event loop
    time.sleep(2)  # Should use asyncio.sleep()
    print("Task completed")


async def blocking_requests_call():
    """Using blocking requests library in async function."""
    # This blocks the event loop - should use aiohttp
    response = requests.get("https://api.example.com/data")
    return response.json()


async def nested_asyncio_run():
    """Calling asyncio.run() inside async context."""
    async def inner_task():
        await asyncio.sleep(0.1)
        return "done"

    # This will fail - asyncio.run() can't be called from async context
    result = asyncio.run(inner_task())
    return result


async def fire_and_forget_task():
    """Creating tasks without storing reference or awaiting."""
    async def background_work():
        await asyncio.sleep(5)
        print("Background work done")

    # Fire-and-forget without storing task reference
    # Could be garbage collected, causing issues
    asyncio.create_task(background_work())

    # Also missing proper error handling
    asyncio.create_task(background_work())

    return "main work done"


def sync_iteration_over_async():
    """Using sync iteration over async iterator."""
    async def async_generator():
        for i in range(3):
            yield i
            await asyncio.sleep(0.1)

    # This won't work - need async for loop
    for item in async_generator():
        print(item)


async def mixed_async_sync_patterns():
    """Mixing various async/sync anti-patterns."""
    # Multiple issues in one function
    data = requests.get("https://api.example.com")  # Blocking call
    time.sleep(1)  # Blocking sleep

    # Missing await
    task_result = asyncio.sleep(0.5)

    # Fire-and-forget
    asyncio.create_task(fetch_data_missing_await())

    return data.json()