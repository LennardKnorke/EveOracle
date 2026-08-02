import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth"; 
import "./Navbar.css";


function Navbar() {
    const navigate = useNavigate();
    const { user, logout } = useAuth();

    const handleLogout = async () => {
        await logout(); // clears cookie, clears context state
        navigate('/');  // App will render <Login /> because user is null
    };

    return (
        <nav className="navbar">
            <div className="navbar-brand">
                <Link to="/">EVE Oracle</Link>
            </div>
            <div className="navbar-menu">
                <Link to="/EveOracleUI">Eve Oracle UI</Link>
                <Link to="/ModelDojo">Model Dojo</Link>
                <Link to="/DataDesigner">Dataset Designer</Link>
                <Link to="/Settings">Settings</Link>
            </div>
            <div className="navbar-user">
            <span>👤 {user?.char_name || "Unknown Pilot"}</span>
                <button onClick={handleLogout} className="logout-btn">
                    Logout
                </button>
            </div>
        </nav>
    );
}

export default Navbar;