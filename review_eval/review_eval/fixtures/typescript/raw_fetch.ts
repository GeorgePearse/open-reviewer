// BAD: Using raw fetch instead of apiFetch/getJson helpers
// Expected issues: fetch, apiFetch, getJson, helper

async function getUsers(): Promise<User[]> {
  // Should use apiFetch or getJson helper instead
  const response = await fetch("/api/users", {
    headers: {
      "Content-Type": "application/json",
    },
  });
  return response.json();
}

async function createUser(data: UserInput): Promise<User> {
  // Raw fetch without proper error handling
  const response = await fetch("/api/users", {
    method: "POST",
    body: JSON.stringify(data),
  });
  return response.json();
}

interface User {
  id: number;
  name: string;
}

interface UserInput {
  name: string;
}
