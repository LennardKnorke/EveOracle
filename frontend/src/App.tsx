// frontend/src/App.tsx

import { Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import EveOracleUI from "./pages/EveOracleUI";
import ModelDojo from "./pages/ModelDojo";
import DataDesignerUI from "./pages/DataDesigner";
import Login from "./pages/Login";
import Navbar from "./components/Navbar";
import { useAuth } from "./auth";
import Settings from "./pages/Settings";



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
            <Route path="/ModelDojo" element={<ModelDojo />} />
            <Route path="/DataDesigner" element={<DataDesignerUI />} />
            <Route path="/Settings" element={<Settings />} />
          </Routes>
        </>
      );
};

export default App;



