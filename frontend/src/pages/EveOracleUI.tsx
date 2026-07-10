//frontend/src/pages/EveOracleUI.tsx

import React, { useState } from 'react';
import { fetch_zkill_char_stats } from "../api/zkill";
import TeamConstellation from "../components/TeamConstellation";
import "./EveOracleUI.css"; 

function EveOracleUI() {
    const [characterInput, setCharacterInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    const [allies, setAllies] = useState<string[]>([]);
    const [neutrals, setNeutrals] = useState<string[]>([]);


    const handleFetch = async () => {
        // Split input by newline, filter empty lines, trim whitespace
        const characters = characterInput
            .split('\n')
            .map(name => name.trim())
            .filter(name => name.length > 0);
        
        if (characters.length === 0) {
            setError('Please enter at least one character name.');
            return;
        }

        const session_key = localStorage.getItem('session_key');
        if (!session_key) {
            setError('No session found. Please log in again.');
            return;
        }

        setLoading(true);
        setError(null);
        setResults(null);

        try {
            const data = await fetch_zkill_char_stats(session_key, characters);
            setResults(data);

            const userCharName = localStorage.getItem('char_name');
            const allResults = data.results || [];
            if (allResults.length === 0) {
                setAllies([]);
                setNeutrals([]);
                return;
            }

            // Find the current user's character in the results
            const userEntry = allResults.find(
                (entry: any) => entry.info?.name?.toLowerCase() === userCharName?.toLowerCase()
            );

            let userAllianceId = null;
            if (userEntry && userEntry.info) {
                userAllianceId = userEntry.info.allianceID || null;
            }

            // If we couldn't find the user, treat everyone as neutral
            if (!userAllianceId) {
                const allNames = allResults.map((entry: any) => entry.info?.name).filter(Boolean);
                setAllies([]);
                setNeutrals(allNames);
                return;
            }

            // Classify each character
            const alliesList: string[] = [];
            const neutralsList: string[] = [];

            allResults.forEach((entry: any) => {
                const name = entry.info?.name;
                if (!name) return;
                const allianceId = entry.info?.allianceID || null;
                if (allianceId === userAllianceId) {
                    alliesList.push(name);
                } else {
                    neutralsList.push(name);
                }
            });

            setAllies(alliesList);
            setNeutrals(neutralsList);
        } catch (err: any) {
            setError(err.message || 'Failed to fetch stats.');
            setAllies([]);
            setNeutrals([]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="eve-oracle-ui">
            <h2>EVE Oracle UI</h2>

                        <div className="ui-layout">
                {/* Left: Input area */}
                <div className="input-area">
                    <p>Paste character names (one per line):</p>
                    <textarea
                        value={characterInput}
                        onChange={(e) => setCharacterInput(e.target.value)}
                        rows={10}
                        cols={40}
                        placeholder="Enter characters here..."
                        className="character-textarea"
                    />
                    <br />
                    <button onClick={handleFetch} disabled={loading}>
                        {loading ? 'Fetching...' : 'Fetch Stats'}
                    </button>
                    {error && <div className="error">{error}</div>}
                </div>

                {/* Right: Team constellation */}
                <div className="team-area">
                    <TeamConstellation allies={allies} neutrals={neutrals} />
                </div>
            </div>

            {/* Logging area (below) */}
            {results && (
                <div className="results">
                    <h3>Raw Results (debug)</h3>
                    <pre>{JSON.stringify(results, null, 2)}</pre>
                </div>
            )}
        </div>
    );
}

export default EveOracleUI;