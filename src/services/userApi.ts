import api from "./api";

export interface User {
  id: string;
  name: string;
  email: string;
  address?: string;
}

export async function getUserProfile(): Promise<User> {
  try {
    const response = await api.get("/users/profile");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch user profile:", error);
    throw error;
  }
}

export async function updateUserProfile(user: Partial<User>): Promise<User> {
  try {
    const response = await api.put("/users/profile", user);
    return response.data;
  } catch (error) {
    console.error("Failed to update user profile:", error);
    throw error;
  }
}