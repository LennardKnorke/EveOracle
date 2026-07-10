// frontend/src/pages/Home.tsx

import TargetCard from "../components/TargetCard";

import "./Home.css";


function Home() {
    return (
        <div className="home">

            <h1>Welcome</h1>
            <p>Yey</p>  
            <div className="card-container">
                <TargetCard
                    title="Eve Oracle"
                    description="Review Local Intel."
                    link="/EveOracleUI"
                />   
                <TargetCard
                    title="Model Dojo"
                    description="Oversee AI Model Training (IN DEV!)."
                    link="/ModelDojo"
                />
            </div>
        </div>
    );
};
  
export default Home;