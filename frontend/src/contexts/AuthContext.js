import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
      return response.data;
    } catch (error) {
      setUser(null);
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

  const startEmailAuth = async (email) => {
    const response = await axiosInstance.post('/auth/email/start', { email });
    return response.data;
  };

  const verifyEmailCode = async (email, code) => {
    const response = await axiosInstance.post('/auth/email/verify', { email, code });
    if (response.data.token) {
      localStorage.setItem('session_token', response.data.token);
      setToken(response.data.token);
    }
    setUser(response.data.user);
    return response.data;
  };

  const logout = async () => {
    try {
      await axiosInstance.post('/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
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
    axiosInstance,
    startEmailAuth,
    verifyEmailCode,
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
