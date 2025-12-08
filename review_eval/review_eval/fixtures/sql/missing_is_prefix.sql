-- BAD: Boolean columns without is_ prefix
-- Expected issues: is_ prefix, boolean, naming convention

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    -- Should be is_active
    active BOOLEAN DEFAULT true,
    -- Should be is_verified
    verified BOOLEAN DEFAULT false,
    -- Should be is_deleted
    deleted BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users (id),
    -- Should be is_paid
    paid BOOLEAN DEFAULT false,
    -- Should be is_shipped
    shipped BOOLEAN DEFAULT false,
    -- Should be is_completed
    completed BOOLEAN DEFAULT false
);
