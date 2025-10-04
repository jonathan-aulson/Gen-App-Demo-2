export interface AuthResponse {
  token: string;
  user: {
    id: string;
    name: string;
    email: string;
  };
}

export async function loginUser(email: string, password: string): Promise<AuthResponse> {
  // Mock API call
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      if (email === "user@bookhaven.com" && password === "password") {
        resolve({
          token: "mock-jwt-token",
          user: { id: "1", name: "John Doe", email }
        });
      } else {
        reject(new Error("Invalid credentials"));
      }
    }, 800);
  });
}

export async function registerUser(
  name: string,
  email: string,
  password: string
): Promise<AuthResponse> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        token: "mock-jwt-token",
        user: { id: "2", name, email }
      });
    }, 800);
  });
}

export async function loginWithGoogle(): Promise<AuthResponse> {
  // Simulating Google OAuth
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        token: "mock-google-oauth-token",
        user: { id: "3", name: "Google User", email: "googleuser@gmail.com" }
      });
    }, 500);
  });
}