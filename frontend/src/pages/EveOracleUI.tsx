// frontend/src/pages/EveOracleUI/EveOracleUI.tsx

import React, { useEffect, useState } from 'react';
import LocalChatInputField from '../components/EveOracleUI/LocalChatCharacters'

import TeamManagerWindow from "../components/EveOracleUI/TeamManager";
import { type CharacterStats } from '../api/type';
import { useAuth } from '../auth'
import { apiClient } from '../api/client';
import "./EveOracleUI.css";


function EveOracleUI() {
    const { user } = useAuth();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [characterInputs, setCharacterInputs] = useState('');


    const [characters, setCharacters] = useState<CharacterStats[]>([]);
    const [allies, setAllies] = useState<CharacterStats[]>([]);
    const [enemies, setEnemies] = useState<CharacterStats[]>([]);
    const [neutrals, setNeutrals] = useState<CharacterStats[]>([]);

    function fetchUserFleet(id : string) {
        const fleet_team = apiClient(`/char/currentFleet?char_id=${user?.id}`);
        console.log(fleet_team);
        // Add chars to 'characters' and 'allies' if they are not already in there
    };

    async function fetchCharacters(names : string[]) {
        setLoading(true);
        setError(null);

        try {
            // Ignore names already in characters list
            const data = await apiClient(`/char/stats`, {
                method : 'POST',
                body: JSON.stringify({char_names : names})
            });
            console.log(data);
            setLoading(false);
            return data;
        } catch (err : any) {
            setError(err.message || "Failed to fetch characters");
            setLoading(false);
            return null;
        }
    };
    const handleFetchCharacters = () => {
        // Fetch Existing names
        const existingNames = new Set(
            characters.map((c) => c.char.char_name.toLowerCase())
        );
        // Set input up input array
        const namesArray = characterInputs
            .split('\n')
            .map(name => name.trim())
            .filter(name => name.length > 0)
            .filter((name) => !existingNames.has(name.toLowerCase()));

        if (namesArray.length === 0) {
            setError("Please enter at least one character name.");
            return;
        }
        // Fetch data
        const data = fetchCharacters(namesArray);
        if (!data) return;
        const newCharacters: CharacterStats[] = Array.isArray(data)
            ? data
            : Object.values(data);
        //Append to arrays
        setCharacters((prev) => [...prev, ...newCharacters]);
        //setNeutrals((prev) => [...prev, ...newCharacters]);
        setCharacterInputs('');
    };
    const handleFetchFleet = () => {

    };

    

    return (
        <div className="eve-oracle-ui">
            <h2>EVE Oracle UI</h2>
            <div className="ui-layout">
                {/* Top Row: Input + Updater */}
                <div className="ui-toprow">
                    <LocalChatInputField 
                        value={characterInputs} 
                        onChange={setCharacterInputs} 
                    />

                    <button onClick={handleFetchCharacters} disabled={loading}>
                        {loading ? 'Fetching...' : 'Fetch Characters'}
                    </button>
                    {error && <div className="error">{error}</div>}

                    <button onClick={handleFetchFleet} disabled={loading}>
                        {loading ? 'Updating...' : 'Update Fleetmembers'}
                    </button>
                </div>


                {/* Middle Row: Manage Team set ups */}
                <div className='ui-teamsrow'>
                    <p>LATER</p>
                </div>

                {/* Bottom Row: Matchup Dashboard */}
                <div className="ui-mainrow">
                    <p>Matchup Row</p>
                </div>

            </div>
        </div>
    );
};

export default EveOracleUI;