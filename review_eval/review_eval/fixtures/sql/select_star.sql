-- BAD: Using SELECT * instead of explicit columns
-- Expected issues: SELECT *, explicit columns, specific columns

-- Should list specific columns
SELECT * FROM users
WHERE is_active = true;

-- Should list specific columns
SELECT * FROM orders AS o
INNER JOIN users AS u ON o.user_id = u.id
WHERE o.is_completed = false;

-- Should list specific columns
CREATE VIEW active_users AS
SELECT * FROM users
WHERE is_deleted = false;

-- Also bad: TIMESTAMP without TIME ZONE
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    name TEXT,
    -- Should be TIMESTAMP WITH TIME ZONE
    event_date TIMESTAMP,
    created_at TIMESTAMP
);
