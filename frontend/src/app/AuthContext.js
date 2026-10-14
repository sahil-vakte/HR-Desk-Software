import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api, clearCsrf, errorMessage } from '../lib/api';
const AuthContext = createContext(null);
export function AuthProvider({ children }) {
  const [state, setState] = useState({ status: 'loading', user: null, menu: [], permissions: [] });
  const reload = useCallback(async () => {
    try { const { data } = await api.get('session/'); setState({ ...data, status: 'authenticated' }); return data; }
    catch (error) {
      if (error.response?.status === 401) setState({ status: 'anonymous', user: null, menu: [], permissions: [] });
      else setState({ status: 'error', user: null, menu: [], permissions: [], message: errorMessage(error) });
      return null;
    }
  }, []);
  useEffect(() => { reload(); }, [reload]);
  useEffect(() => {
    const interceptor = api.interceptors.response.use(value => value, error => {
      if (error.response?.status === 401 && !error.config?.url?.includes('session/')) {
        clearCsrf(); setState({ status: 'anonymous', user: null, menu: [], permissions: [], expired: true });
      }
      return Promise.reject(error);
    });
    return () => api.interceptors.response.eject(interceptor);
  }, []);
  const signOut = async () => { await api.post('auth/logout/'); clearCsrf(); await reload(); };
  return <AuthContext.Provider value={{ ...state, reload, signOut }}>{children}</AuthContext.Provider>;
}
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
