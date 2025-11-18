import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiService } from '../services/api';

interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  department: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check if user is authenticated on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const userData = await apiService.getCurrentUser();
          setUser(userData);
        } catch (error) {
          // Token is invalid, remove it
          localStorage.removeItem('token');
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      console.log('AuthContext: Attempting login for username:', username);
      const response = await apiService.login(username, password);
      console.log('AuthContext: Login response:', response);
      
      if (response && response.access_token && response.user_info) {
        localStorage.setItem('token', response.access_token);
        setUser(response.user_info as User);
        console.log('AuthContext: Login successful, user set:', response.user_info);
        return true;
      } else {
        console.error('AuthContext: Invalid response format:', response);
        return false;
      }
    } catch (error) {
      console.error('AuthContext: Login failed with error:', error);
      if (error instanceof Error) {
        console.error('AuthContext: Error message:', error.message);
        console.error('AuthContext: Error stack:', error.stack);
      }
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  const refreshUser = async () => {
    try {
      const userData = await apiService.getCurrentUser();
      setUser(userData);
    } catch (error) {
      console.error('Failed to refresh user data:', error);
      logout();
    }
  };

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    refreshUser
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};