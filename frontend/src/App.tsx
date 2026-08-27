// frontend/src/App.tsx

import { Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
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
            <Route path="/" element={<Home />} />
            <Route path="/EveOracleUI" element={<EveOracleUI />} />
          </Routes>
        </>
      );
};

export default App;



