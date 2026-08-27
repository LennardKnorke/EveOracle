// frontend/src/auth.tsx
import React, { createContext, useContext, useEffect, useState } from 'react';
import { apiClient } from './api/client'; 

interface User {
    char_name: string;
    id: string;
};


interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: () => void;
    logout: () => Promise<void>;
};


const AuthContext = createContext<AuthContextType | undefined>(undefined);
const API_BASE = 'http://localhost:8080';


export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
  
    const checkAuth = async () => {
        try {
            const data = await apiClient<{ char_name: string; id: string }>('/auth/me');
            setUser({ char_name: data.char_name, id: data.id });
        } catch {
            setUser(null);
        } finally {
            setLoading(false);
        };
    };
  
    useEffect(() => {
        checkAuth();
        const handleUnauthorized = () => {
            setUser(null);
            // Optionally redirect to home or login
            window.location.href = '/';
        };
        window.addEventListener('auth:unauthorized', handleUnauthorized);
      
        return () => {
            window.removeEventListener('auth:unauthorized', handleUnauthorized);
        };
    }, []);
  
    const login = () => {
        window.location.href = `${API_BASE}/auth/sso_login`;
    };
  
    const logout = async () => {
        try {
            await apiClient('/auth/logout', { method: 'POST' });
        } catch {
            // ignore errors on logout
        } finally {
            setUser(null);
            window.location.href = '/';
        }
    };
  
    return (
        <AuthContext.Provider value={{ user, loading, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
};


export const useAuth = () => {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used within AuthProvider');
    return ctx;
};