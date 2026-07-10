// frontend/src/components/TeamViewer.tsx
import React from 'react';
import './TeamConstellation.css';


interface TeamConstellationProps {
    allies: string[];
    neutrals: string[];
    enemies?: string[]; // for future use
}


const TeamConstellation: React.FC<TeamConstellationProps> = ({ allies, neutrals, enemies = [] }) => {
    return (
        <div className="team-constellation">
            <div className="column">
                <h3>Allies</h3>
                <ul>
                    {allies.length > 0 ? allies.map((name, idx) => <li key={idx}>{name}</li>) : <li className="empty">—</li>}
                </ul>
            </div>
            <div className="column">
                <h3>Enemies</h3>
                <ul>
                    {enemies.length > 0 ? enemies.map((name, idx) => <li key={idx}>{name}</li>) : <li className="empty">—</li>}
                </ul>
            </div>
            <div className="column">
                <h3>Neutrals</h3>
                <ul>
                    {neutrals.length > 0 ? neutrals.map((name, idx) => <li key={idx}>{name}</li>) : <li className="empty">—</li>}
                </ul>
            </div>
        </div>
    );
};

export default TeamConstellation;