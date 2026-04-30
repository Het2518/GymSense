import React, { createContext, useContext, useState, useEffect } from 'react';
import { login, register, getMe } from '../api';
import toast from 'react-hot-toast';

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('gymsense_token') || null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      if (token) {
        try {
          const userData = await getMe();
          setUser(userData);
        } catch (err) {
          console.error("Failed to load user:", err);
          if (err.message === 'UNAUTHORIZED') {
            logout();
          }
        }
      }
      setLoading(false);
    }
    loadUser();
  }, [token]);

  const handleLogin = async (email, password) => {
    try {
      const data = await login(email, password);
      localStorage.setItem('gymsense_token', data.access_token);
      setToken(data.access_token);
      toast.success('Logged in successfully');
      return true;
    } catch (err) {
      toast.error(err.message || 'Login failed');
      return false;
    }
  };

  const handleRegister = async (name, email, password) => {
    try {
      const data = await register(name, email, password);
      localStorage.setItem('gymsense_token', data.access_token);
      setToken(data.access_token);
      toast.success('Registration successful');
      return true;
    } catch (err) {
      toast.error(err.message || 'Registration failed');
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('gymsense_token');
    setToken(null);
    setUser(null);
    toast.success('Logged out');
  };

  const value = {
    user,
    token,
    loading,
    setUser,
    login: handleLogin,
    register: handleRegister,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}
