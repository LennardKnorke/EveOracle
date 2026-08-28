// frontend/src/App.tsx

import { Routes, Route, Navigate } from "react-router-dom";

import EveOracleUI from "./pages/EveOracleUI";
import Login from "./pages/Login";

import Navbar from "./components/Navbar";
import { useAuth } from "./auth";



function App() {
    const { user, loading, login } = useAuth();

    if (loading) return <div>Loading...</div>;
    if (!user) {
        return <Login onLogin={login} />;
    }

    return (
        <>
          <Navbar />
          <Routes>
            <Route path="/EveOracleUI" element={<EveOracleUI />} />
            {/* Catch-all: redirect root and any other path to /EveOracleUI */}
            <Route path="*" element={<Navigate to="/EveOracleUI" replace />} />
          </Routes>
        </>
      );
};

export default App;



