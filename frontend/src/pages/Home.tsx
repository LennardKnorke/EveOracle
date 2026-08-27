// frontend/src/pages/Home.tsx

import MenuCard from "../components/Home/MenuCard";
import { useAuth } from "../auth"; 
import "./Home.css";


function Home() {
    const { user, logout } = useAuth();

    return (
        <div className="home">

            <h1>Welcome {user?.char_name || "Unknown Pilot"}</h1>
            
            <div className="card-container">
                <MenuCard
                    title="Eve Oracle"
                    description="Review Local Intel."
                    link="/EveOracleUI"
                />
            </div>
        </div>
    );
};
  
export default Home;