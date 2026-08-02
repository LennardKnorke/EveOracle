// frontend/src/App.tsx

import { Routes, Route, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

import Home from "./pages/Home";
import EveOracleUI from "./pages/EveOracleUI";
import ModelDojo from "./pages/ModelDojo";
import DataDesignerUI from "./pages/DataDesigner";
import Login from "./pages/Login";
import Navbar from "./components/Navbar";
import { validate_session } from "./api/auth";
import Settings from "./pages/Settings";



function App() {
    const location = useLocation();
    const navigate = useNavigate();
    const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

    useEffect(() => {
        // 1. Check for session_key in URL query parameters
        const params = new URLSearchParams(location.search);
        const sessionKeyFromUrl = params.get('session_key');
        
        if (sessionKeyFromUrl) {
            // Store it in localStorage
            localStorage.setItem('session_key', sessionKeyFromUrl);
            // Remove the query param from the URL without reloading
            navigate(location.pathname, { replace: true });
        }

        // 2. Now check if we have a session key
        const session_key = localStorage.getItem('session_key');
        if (!session_key) {
            setIsAuthenticated(false);
            return;
        }

        // 3. Validate the session asynchronously
        validate_session(session_key)
            .then(({ session_key : validKey, char_name, char_id }) => {
                if (validKey) {
                    localStorage.setItem('char_name', char_name || '');
                    localStorage.setItem('char_id', char_id || '');
                    setIsAuthenticated(true);
                } else {
                    localStorage.removeItem('session_key');
                    localStorage.removeItem('char_name');
                    localStorage.removeItem('char_id');
                    setIsAuthenticated(false);
                }
            })
            .catch(() => {
                setIsAuthenticated(false);
                localStorage.removeItem('session_key');
                localStorage.removeItem('char_name');
                localStorage.removeItem('char_id');
            });
    }, [location, navigate]); 

    if (isAuthenticated === null) {
        return <div>Loading...</div>; // or a spinner
    }

    if (!isAuthenticated) {
        return <Login />;
    }

    return (
        <>
            <Navbar />
            <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/EveOracleUI" element={<EveOracleUI />} />
                <Route path="/ModelDojo" element={<ModelDojo />} />
                <Route path="/DataDesigner" element={<DataDesignerUI />} />
                <Route path="/Settings" element={<Settings/>} />
            </Routes>
        </>
    );
};

export default App;



