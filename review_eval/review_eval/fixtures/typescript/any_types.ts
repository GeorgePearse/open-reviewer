// BAD: Using any types
// Expected issues: any, type safety, specific type, unknown

function processData(data: any): any {
  return data.result;
}

const config: any = {
  apiUrl: "https://api.example.com",
};

function handleResponse(response: any) {
  const items: any[] = response.items;
  items.forEach((item: any) => {
    console.log(item.name);
  });
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function legacyFunction(input: any): any {
  return input;
}
