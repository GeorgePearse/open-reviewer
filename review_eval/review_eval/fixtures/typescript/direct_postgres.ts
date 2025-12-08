// BAD: Direct Postgres queries instead of GraphQL
// Expected issues: postgres, GraphQL, direct query, database

import { Pool } from "pg";

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

// Should use GraphQL instead of direct database queries
async function getUsers() {
  const result = await pool.query("SELECT * FROM users");
  return result.rows;
}

async function getUserById(id: number) {
  const result = await pool.query("SELECT * FROM users WHERE id = $1", [id]);
  return result.rows[0];
}

async function createUser(name: string, email: string) {
  const result = await pool.query(
    "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING *",
    [name, email],
  );
  return result.rows[0];
}
