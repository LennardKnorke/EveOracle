// frontend/src/api/auth.ts
import React, { createContext, useContext, useEffect, useState } from 'react';

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
            const res = await fetch(`${API_BASE}/auth/me`, {
                credentials: 'include', // sends the cookie
            });
            if (res.ok) {
                const data = await res.json();
                setUser({ char_name: data.char_name, id: data.id });
            } else {
                setUser(null);
            }
        } catch {
            setUser(null);
        } finally {
            setLoading(false);
        }
    };
  
    useEffect(() => {
        checkAuth();
    }, []);
  
    const login = () => {
        window.location.href = `${API_BASE}/auth/sso_login`;
    };
  
    const logout = async () => {
        await fetch(`${API_BASE}/auth/logout`, {
            method: 'POST',
            credentials: 'include',
        });
        setUser(null);
        // optionally redirect to login
        window.location.href = '/';
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