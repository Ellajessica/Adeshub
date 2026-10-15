import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { User, Address, AddressInput, RegisterPayload } from '../types/api';
import { api, getStoredAuthToken } from '../services/api';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  addresses: Address[];
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  updateProfile: (data: Partial<{ first_name: string; last_name: string; phone_number: string; email: string }>) => Promise<User>;
  changePassword: (currentPassword: string, newPassword: string, newPasswordConfirm: string) => Promise<void>;
  fetchAddresses: () => Promise<Address[]>;
  addAddress: (data: AddressInput) => Promise<Address>;
  editAddress: (id: number, data: Partial<AddressInput>) => Promise<Address>;
  removeAddress: (id: number) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchAddresses = useCallback(async (): Promise<Address[]> => {
    try {
      const data = await api.getAddresses();
      setAddresses(data);
      return data;
    } catch {
      setAddresses([]);
      return [];
    }
  }, []);

  const loadCurrentUser = useCallback(async () => {
    const token = getStoredAuthToken();
    if (!token) {
      setUser(null);
      setAddresses([]);
      setIsLoading(false);
      return;
    }

    try {
      const userData = await api.getProfile();
      setUser(userData);
      await fetchAddresses();
    } catch {
      // Invalid/expired token
      setUser(null);
      setAddresses([]);
    } finally {
      setIsLoading(false);
    }
  }, [fetchAddresses]);

  useEffect(() => {
    loadCurrentUser();
  }, [loadCurrentUser]);

  const login = async (email: string, password: string) => {
    const res = await api.login(email, password);
    setUser(res.user);
    await fetchAddresses();
  };

  const register = async (data: RegisterPayload) => {
    const res = await api.register(data);
    setUser(res.user);
    await fetchAddresses();
  };

  const logout = async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
      setAddresses([]);
    }
  };

  const updateProfile = async (data: Partial<{ first_name: string; last_name: string; phone_number: string; email: string }>): Promise<User> => {
    const updated = await api.updateProfile(data);
    setUser(updated);
    return updated;
  };

  const changePassword = async (currentPassword: string, newPassword: string, newPasswordConfirm: string) => {
    await api.changePassword(currentPassword, newPassword, newPasswordConfirm);
  };

  const addAddress = async (data: AddressInput): Promise<Address> => {
    const newAddr = await api.createAddress(data);
    await fetchAddresses();
    return newAddr;
  };

  const editAddress = async (id: number, data: Partial<AddressInput>): Promise<Address> => {
    const updatedAddr = await api.updateAddress(id, data);
    await fetchAddresses();
    return updatedAddr;
  };

  const removeAddress = async (id: number): Promise<void> => {
    await api.deleteAddress(id);
    await fetchAddresses();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        addresses,
        login,
        register,
        logout,
        updateProfile,
        changePassword,
        fetchAddresses,
        addAddress,
        editAddress,
        removeAddress,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
