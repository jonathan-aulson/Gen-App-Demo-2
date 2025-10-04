import React, { useEffect, useState } from "react";
import { fetchUserProfile, updateUserProfile, UserProfile } from "../services/userService";
import { useAppSelector, useAppDispatch } from "../store/hooks";
import { setUser } from "../store/slices/userSlice";

const UserAccount: React.FC = () => {
  const userState = useAppSelector((state) => state.user);
  const dispatch = useAppDispatch();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const userProfile = await fetchUserProfile();
        setProfile(userProfile);
      } catch (error) {
        setErrorMessage("Failed to load profile data.");
      } finally {
        setLoading(false);
      }
    };
    loadProfile();
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (profile) {
      setProfile({ ...profile, [e.target.name]: e.target.value });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (profile) {
      setSuccessMessage("");
      setErrorMessage("");
      try {
        const updated = await updateUserProfile(profile);
        setProfile(updated);
        dispatch(setUser({ ...userState, name: updated.name, email: updated.email }));
        setSuccessMessage("Profile updated successfully!");
      } catch (error) {
        setErrorMessage("Failed to update profile.");
      }
    }
  };

  if (loading) {
    return <p className="text-center text-gray-600 mt-8">Loading profile...</p>;
  }

  if (!profile) {
    return <p className="text-center text-red-600 mt-8">Unable to load profile data.</p>;
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <h2 className="text-3xl font-bold text-navy-700 mb-6 text-center">Your Account</h2>
      <form onSubmit={handleSubmit} className="bg-white shadow-md rounded p-6 space-y-4">
        {successMessage && (
          <p className="text-green-600 text-sm text-center">{successMessage}</p>
        )}
        {errorMessage && <p className="text-red-600 text-sm text-center">{errorMessage}</p>}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
          <input
            type="text"
            name="name"
            value={profile.name}
            onChange={handleChange}
            required
            className="w-full border rounded p-2 focus:outline-none focus:border-navy-700"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            type="email"
            name="email"
            value={profile.email}
            onChange={handleChange}
            required
            className="w-full border rounded p-2 bg-gray-100 cursor-not-allowed"
            disabled
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
          <input
            type="text"
            name="address"
            value={profile.address}
            onChange={handleChange}
            required
            className="w-full border rounded p-2 focus:outline-none focus:border-navy-700"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Payment Method</label>
          <input
            type="text"
            name="paymentMethod"
            value={profile.paymentMethod}
            onChange={handleChange}
            required
            className="w-full border rounded p-2 focus:outline-none focus:border-navy-700"
          />
        </div>

        <button
          type="submit"
          className="btn-primary w-full sm:w-auto mt-4"
        >
          Save Changes
        </button>
      </form>
    </div>
  );
};

export default UserAccount;