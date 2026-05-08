import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { adminStorage, tokenStorage } from '../api/axios.js';
import { authApi } from '../api/endpoints.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [admin, setAdmin] = useState(() => adminStorage.get());
  const [token, setToken] = useState(() => tokenStorage.get());
  const [loading, setLoading] = useState(false);

  const login = useCallback(async (username, password) => {
    setLoading(true);
    try {
      const data = await authApi.login(username, password);
      tokenStorage.set(data.access_token);
      adminStorage.set(data.admin);
      setToken(data.access_token);
      setAdmin(data.admin);
      return data.admin;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    tokenStorage.clear();
    setToken(null);
    setAdmin(null);
  }, []);

  // Keep "admin" object fresh whenever a token is present (e.g. after refresh).
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    authApi
      .me()
      .then((data) => {
        if (cancelled) return;
        adminStorage.set(data);
        setAdmin(data);
      })
      .catch(() => {
        // 401 handler already clears storage.
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const value = useMemo(
    () => ({
      admin,
      token,
      loading,
      isAuthenticated: Boolean(token && admin),
      login,
      logout,
    }),
    [admin, token, loading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
