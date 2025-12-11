# Test Categories

Open Reviewer includes 16+ pre-built test cases across four categories.

## Python Anti-Patterns

### psycopg2 Usage

Using the deprecated `psycopg2` instead of modern `psycopg3`.

```python
# Bad
import psycopg2
conn = psycopg2.connect(...)

# Good
import psycopg
conn = psycopg.connect(...)
```

**Expected issues:** `psycopg2`, `psycopg3`, `deprecated`

### Unsafe YAML Loading

Using `yaml.load()` without a safe loader.

```python
# Bad
import yaml
data = yaml.load(file)

# Good
import yaml
data = yaml.safe_load(file)
```

**Expected issues:** `safe_load`, `yaml.load`, `unsafe`

### Missing Type Annotations

Functions without type hints.

```python
# Bad
def process(data):
    return data.strip()

# Good
def process(data: str) -> str:
    return data.strip()
```

**Expected issues:** `type annotation`, `type hint`, `typing`

### Any Type Abuse

Overuse of `Any` type defeating the purpose of type hints.

```python
# Bad
def process(data: Any) -> Any:
    return data

# Good
def process(data: dict[str, str]) -> list[str]:
    return list(data.values())
```

**Expected issues:** `Any`, `specific type`, `type safety`

### Generic Utils Module

Catch-all utility modules that become dumping grounds.

```python
# Bad: utils.py with unrelated functions
def format_date(): ...
def validate_email(): ...
def calculate_tax(): ...

# Good: Specific modules
# date_utils.py, validators.py, tax.py
```

**Expected issues:** `utils`, `cohesion`, `single responsibility`

### Async/Await Anti-Patterns

Common mistakes in asynchronous Python code.

#### Missing await on coroutine calls

```python
# Bad
async def fetch_data():
    return {"data": "example"}

async def process():
    result = fetch_data()  # Returns coroutine object, not data
    return result

# Good
async def process():
    result = await fetch_data()  # Actually gets the data
    return result
```

**Expected issues:** `await`, `coroutine`, `async`

#### Blocking calls in async functions

```python
# Bad
import time
import requests

async def slow_task():
    time.sleep(2)  # Blocks event loop
    response = requests.get(url)  # Blocks event loop
    return response.json()

# Good
import asyncio
import aiohttp

async def slow_task():
    await asyncio.sleep(2)  # Non-blocking
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

**Expected issues:** `time.sleep`, `asyncio.sleep`, `requests`, `aiohttp`, `blocking`

#### asyncio.run() in async context

```python
# Bad
async def nested_run():
    async def inner():
        return "result"

    # RuntimeError: asyncio.run() cannot be called from running event loop
    result = asyncio.run(inner())
    return result

# Good
async def nested_run():
    async def inner():
        return "result"

    result = await inner()
    return result
```

**Expected issues:** `asyncio.run`, `event loop`, `RuntimeError`

#### Fire-and-forget tasks without references

```python
# Bad
async def create_tasks():
    for i in range(5):
        asyncio.create_task(some_task())  # No reference - may be garbage collected

# Good
async def create_tasks():
    tasks = []
    for i in range(5):
        task = asyncio.create_task(some_task())
        tasks.append(task)

    await asyncio.gather(*tasks)
```

**Expected issues:** `create_task`, `reference`, `garbage collected`

#### Sync iteration over async iterators

```python
# Bad
async def process_items():
    async def async_gen():
        for i in range(3):
            await asyncio.sleep(0.1)
            yield f"item_{i}"

    items = []
    for item in async_gen():  # Wrong - need async for
        items.append(item)

# Good
async def process_items():
    async def async_gen():
        for i in range(3):
            await asyncio.sleep(0.1)
            yield f"item_{i}"

    items = []
    async for item in async_gen():  # Correct async iteration
        items.append(item)
```

**Expected issues:** `async for`, `async generator`, `iteration`

---

## TypeScript Anti-Patterns

### Raw fetch() Usage

Using `fetch()` directly instead of typed API helpers.

```typescript
// Bad
const response = await fetch('/api/users');
const data = await response.json();

// Good
const users = await apiClient.get<User[]>('/users');
```

**Expected issues:** `fetch`, `typed`, `api client`, `wrapper`

### Any Types

Using `any` type instead of proper TypeScript types.

```typescript
// Bad
function process(data: any): any {
  return data.value;
}

// Good
interface Data {
  value: string;
}
function process(data: Data): string {
  return data.value;
}
```

**Expected issues:** `any`, `type`, `interface`

### Default Exports

Using default exports instead of named exports.

```typescript
// Bad
export default function MyComponent() {}

// Good
export function MyComponent() {}
```

**Expected issues:** `default export`, `named export`

### Direct Database Queries

Querying databases directly in components/handlers.

```typescript
// Bad
const users = await db.query('SELECT * FROM users');

// Good
const users = await userRepository.findAll();
```

**Expected issues:** `repository`, `abstraction`, `direct query`

---

## SQL Anti-Patterns

### Missing is_ Prefix for Booleans

Boolean columns without the `is_` prefix convention.

```sql
-- Bad
CREATE TABLE users (
    active BOOLEAN
);

-- Good
CREATE TABLE users (
    is_active BOOLEAN
);
```

**Expected issues:** `is_`, `boolean`, `naming convention`

### VARCHAR(n) Usage

Using `VARCHAR(n)` instead of `TEXT` in PostgreSQL.

```sql
-- Bad
CREATE TABLE users (
    name VARCHAR(255)
);

-- Good
CREATE TABLE users (
    name TEXT
);
```

**Expected issues:** `VARCHAR`, `TEXT`, `PostgreSQL`

### SELECT * Usage

Using `SELECT *` instead of explicit column names.

```sql
-- Bad
SELECT * FROM users;

-- Good
SELECT id, name, email FROM users;
```

**Expected issues:** `SELECT *`, `explicit columns`, `performance`

---

## Security Issues

### SQL Injection

Constructing SQL queries with string formatting.

```python
# Bad
query = f"SELECT * FROM users WHERE id = {user_id}"

# Good
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

**Expected issues:** `SQL injection`, `parameterized`, `prepared statement`

### Hardcoded Secrets

API keys and passwords in source code.

```python
# Bad
API_KEY = "sk-1234567890abcdef"
PASSWORD = "admin123"

# Good
API_KEY = os.environ["API_KEY"]
PASSWORD = os.environ["DB_PASSWORD"]
```

**Expected issues:** `hardcoded`, `secret`, `environment variable`

### Command Injection

Using `shell=True` with untrusted input.

```python
# Bad
subprocess.run(f"ls {user_input}", shell=True)

# Good
subprocess.run(["ls", user_input], shell=False)
```

**Expected issues:** `shell=True`, `command injection`, `subprocess`

---

## Adding Custom Test Cases

Create your own test cases:

```python
from review_eval import GoldenTestCase

test_case = GoldenTestCase(
    id="my-custom-pattern",
    file_path="fixtures/python/my_pattern.py",
    code='''
# Your code with the anti-pattern
def bad_function():
    pass
''',
    expected_issues=["keyword1", "keyword2"],
    severity="high",
    category="python",
)
```

See [How-To: Add Test Cases](../how-to/add-test-cases.md) for details.

---

## Test Categories by Language

| Category | Test Count | Focus |
|----------|-----------|-------|
| Python | 6 | Types, libraries, structure, async/await |
| TypeScript | 4 | Types, patterns, exports |
| SQL | 3 | Naming, performance, PostgreSQL |
| Security | 3 | Injection, secrets, commands |
