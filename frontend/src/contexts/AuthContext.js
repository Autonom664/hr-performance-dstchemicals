import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

// Determine API base URL:
// - If REACT_APP_BACKEND_URL is set and non-empty, use it (for cross-origin or explicit config)
// - Otherwise, use relative '/api' path (for same-origin deployment via nginx proxy)
const getApiBaseUrl = () => {
  const envUrl = process.env.REACT_APP_BACKEND_URL;
  
  // If env var is set and non-empty, use it
  if (envUrl && envUrl.trim() !== '') {
    // Ensure we append /api if not already present
    const baseUrl = envUrl.trim();
    if (baseUrl.endsWith('/api')) {
      return baseUrl;
    }
    return `${baseUrl}/api`;
  }
  
  // Default: same-origin relative path (nginx proxies /api to backend)
  return '/api';
};

const API_URL = getApiBaseUrl();

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('session_token'));
  const [mustChangePassword, setMustChangePassword] = useState(false);

  const axiosInstance = axios.create({
    baseURL: API_URL,
    withCredentials: true,
  });

  // Add auth header to all requests
  axiosInstance.interceptors.request.use((config) => {
    const storedToken = localStorage.getItem('session_token');
    if (storedToken) {
      config.headers.Authorization = `Bearer ${storedToken}`;
    }
    return config;
  });

  const fetchUser = useCallback(async () => {
    try {
      const response = await axiosInstance.get('/auth/me');
      setUser(response.data);
      setMustChangePassword(response.data.must_change_password || false);
      return response.data;
    } catch (error) {
      setUser(null);
      setMustChangePassword(false);
      localStorage.removeItem('session_token');
      setToken(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [token, fetchUser]);

  // Password-based login
  const login = async (email, password) => {
    const response = await axiosInstance.post('/auth/login', { email, password });
    if (response.data.token) {
      localStorage.setItem('session_token', response.data.token);
      setToken(response.data.token);
    }
    setUser(response.data.user);
    setMustChangePassword(response.data.must_change_password || false);
    return response.data;
  };

  // Change password
  const changePassword = async (currentPassword, newPassword) => {
    const response = await axiosInstance.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    setMustChangePassword(false);
    return response.data;
  };

  const logout = async () => {
    try {
      await axiosInstance.post('/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      setMustChangePassword(false);
      localStorage.removeItem('session_token');
      setToken(null);
    }
  };

  const hasRole = (role) => {
    return user?.roles?.includes(role) || false;
  };

  const isAdmin = () => hasRole('admin');
  const isManager = () => hasRole('manager') || hasRole('admin');
  const isEmployee = () => hasRole('employee');

  const value = {
    user,
    loading,
    token,
    mustChangePassword,
    axiosInstance,
    login,
    changePassword,
    logout,
    fetchUser,
    hasRole,
    isAdmin,
    isManager,
    isEmployee,
    API_URL,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;
