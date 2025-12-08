-- BAD: Using varchar(n) instead of TEXT
-- Expected issues: varchar, TEXT, don't use varchar

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    -- Should use TEXT instead of varchar(n)
    name VARCHAR(255) NOT NULL,
    description VARCHAR(1000),
    sku VARCHAR(50) NOT NULL,
    category VARCHAR(100),
    brand VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    -- Should use TEXT
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    address VARCHAR(500)
);
