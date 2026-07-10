import { Link, useNavigate } from "react-router-dom";

import "./Navbar.css";


function Navbar() {
    const navigate = useNavigate();
    const charName = localStorage.getItem('char_name') || "Unknown Pilot";

    const handleLogout = () => {
        localStorage.removeItem('session_key');
        localStorage.removeItem('char_name');
        navigate('/'); // or navigate('/login') if you have a dedicated login route
        // Optionally force a page reload to reset state
        window.location.reload();
    };

    return (
        <nav className="navbar">
            <div className="navbar-brand">
                <Link to="/">EVE Oracle</Link>
            </div>
            <div className="navbar-menu">
                <Link to="/EveOracleUI">Eve Oracle UI</Link>
                <Link to="/ModelDojo">Model Dojo</Link>
                <Link to="/Settings">Settings</Link>
            </div>
            <div className="navbar-user">
                <span>👤 {charName}</span>
                <button onClick={handleLogout} className="logout-btn">Logout</button>
            </div>
        </nav>
    );
}

export default Navbar;