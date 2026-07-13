// frontend/src/pages/Home.tsx

import MenuCard from "../components/MenuCard";

import "./Home.css";


function Home() {
    const username = localStorage.getItem("char_name");
    return (
        <div className="home">

            <h1>Welcome {username}</h1>
            
            <div className="card-container">
                <MenuCard
                    title="Eve Oracle"
                    description="Review Local Intel."
                    link="/EveOracleUI"
                />   
                <MenuCard
                    title="Model Dojo"
                    description="Oversee AI Model Training (IN DEV!)."
                    link="/ModelDojo"
                />
            </div>
        </div>
    );
};
  
export default Home;