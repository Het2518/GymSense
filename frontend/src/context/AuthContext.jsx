import React, { createContext, useContext, useState, useEffect } from 'react';
import { login, register, getMe } from '../api';
import toast from 'react-hot-toast';
import Cookies from 'js-cookie';

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(Cookies.get('gymsense_token') || null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      if (token) {
        try {
          const userData = await getMe();
          setUser(userData);
        } catch (err) {
          console.error("Failed to load user:", err);
          const msg = err.message || '';
          
          if (msg.includes('UNAUTHORIZED') || 
              msg.includes('Could not validate credentials') || 
              msg.includes('Signature has expired') || 
              msg.includes('HTTP 401')) {
            // Token is legitimately invalid or expired. Clear session.
            toast.error('Session expired. Please log in again.');
            logout();
          } else if (msg.includes('HTTP 50') || msg.includes('Failed to fetch')) {
            // Backend is temporarily down or restarting due to OOM
            toast.error('Cannot connect to server. It might be waking up.');
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
      Cookies.set('gymsense_token', data.access_token, { expires: 2 });
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
      Cookies.set('gymsense_token', data.access_token, { expires: 2 });
      setToken(data.access_token);
      toast.success('Registration successful');
      return true;
    } catch (err) {
      toast.error(err.message || 'Registration failed');
      return false;
    }
  };

  const logout = () => {
    Cookies.remove('gymsense_token');
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
