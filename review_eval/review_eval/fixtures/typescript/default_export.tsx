// BAD: Using default export instead of named export
// Expected issues: default export, named export

interface UserProps {
  name: string;
  email: string;
}

function UserComponent({ name, email }: UserProps) {
  return (
    <div>
      <h1>{name}</h1>
      <p>{email}</p>
    </div>
  );
}

// Should use named export: export { UserComponent }
export default UserComponent;
