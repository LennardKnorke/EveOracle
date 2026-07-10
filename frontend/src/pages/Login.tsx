// frontend/src/pages/Login.tsx
import "./Home.css";

import ssoButton from "../assets/eve-sso-login-black-large.png";

const login = () => {
    const sso_url = "http://localhost:8080/auth/sso_login";
    window.location.href = sso_url;
};

function Login() {
    return (
        <div className="home">
            <h1>EVE Oracle</h1>

            <p>Login using your EVE Online account.</p>

            <img 
                src={ssoButton} 
                alt="Login with EVE Online" 
                onClick={login} 
                className="sso-button"
            />
        </div>
    );
}

export default Login;