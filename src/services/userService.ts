export interface UserProfile {
  id: string;
  name: string;
  email: string;
  address: string;
  paymentMethod: string;
}

export async function fetchUserProfile(): Promise<UserProfile> {
  // Mocked API call
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        id: "1",
        name: "John Doe",
        email: "user@bookhaven.com",
        address: "123 Main St, Springfield",
        paymentMethod: "Visa **** 4242"
      });
    }, 600);
  });
}

export async function updateUserProfile(profile: UserProfile): Promise<UserProfile> {
  // Mock saving to backend
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(profile);
    }, 600);
  });
}