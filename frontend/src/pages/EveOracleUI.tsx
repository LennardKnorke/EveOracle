//frontend/src/pages/EveOracleUI.tsx

import React, { useState } from 'react';
import { fetch_zkill_char_stats, transformToCharacterStats, type CharacterStats } from "../api/zkill";
import TeamManagerWindow from "../components/TeamManager";
import "./EveOracleUI.css"; 



function EveOracleUI() {
    const [characterInput, setCharacterInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    const [allies, setAllies] = useState<CharacterStats[]>([]);
    const [enemies, setEnemies] = useState<CharacterStats[]>([]);
    const [neutrals, setNeutrals] = useState<CharacterStats[]>([]);

    // Move character between columns
    const moveCharacter = (
        from: 'allies' | 'enemies' | 'neutrals',
        to: 'allies' | 'enemies' | 'neutrals',
        targetChar: CharacterStats
    ) => {
        if (from === to) return;

        // Get current lists
        const lists = { allies, enemies, neutrals };
        const setLists = { allies: setAllies, enemies: setEnemies, neutrals: setNeutrals };

        // Remove from source
        const sourceList = lists[from].filter(char => char.char.char_id !== targetChar.char.char_id);
        // Add
        const targetList = lists[to].some(char => char.char.char_id === targetChar.char.char_id)
            ? lists[to]
            : [...lists[to], targetChar];

        // Update states
        setLists[from](sourceList);
        setLists[to](targetList);
    };

    const removeCharacter = (
        from: 'allies' | 'enemies' | 'neutrals',
        targetChar: CharacterStats
    ) => {
        const lists = { allies, enemies, neutrals };
        const setLists = { allies: setAllies, enemies: setEnemies, neutrals: setNeutrals };
        const sourceList = lists[from].filter(char => char.char.char_id !== targetChar.char.char_id);
        setLists[from](sourceList);
    };


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
            // TODO: Transform before passing setting each list.
            const data : CharacterStats[] = await fetch_zkill_char_stats(session_key, characters);
            const CharStats = transformToCharacterStats(data);
            
            setResults(CharStats);

            const userCharName = localStorage.getItem('char_name');

            if (CharStats.length === 0) {
                setAllies([]);
                setEnemies([]);
                setNeutrals([]);
                return;
            }

            // Find the current user's character in the results
            const userEntry = CharStats.find(
                (entry: CharacterStats) => entry.char.char_name?.toLowerCase() === userCharName?.toLowerCase()
            );

            let userAllianceId = null;
            if (userEntry && userEntry.char) {
                userAllianceId = userEntry.char.alliance_id || null;
            }

            // If we couldn't find the user, treat everyone as neutral (Properly map to CharacterStats objects)
            if (!userAllianceId) {
                const fallbackNeutrals: CharacterStats[] = CharStats.filter(
                    (entry: CharacterStats) => entry.char?.char_name && entry.char?.char_id
                );

                setAllies([]);
                setEnemies([]);
                setNeutrals(fallbackNeutrals);
                return;
            }

            // Classify each character
            const alliesList: CharacterStats[] = [];
            const enemyList: CharacterStats[] = [];

            CharStats.forEach((entry: CharacterStats) => {
                const name = entry.char?.char_name || null;
                const id = entry.char?.char_id || null;
                const allianceId = entry.char?.alliance_id || null;

                if (!name || !id) return;

                if (userAllianceId && allianceId === userAllianceId) {
                    alliesList.push(entry);
                } else {
                    enemyList.push(entry);
                }
            });

            setAllies(alliesList);
            setNeutrals([]);
            setEnemies(enemyList);
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
                {/* Top Area  - Search and Set up*/}
                <div className='ui-toprow'>
                    {/* Top Left: Input area */}
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

                    {/* Top Right: Team constellation Management*/}
                    <div className="teammanager-area">
                        <TeamManagerWindow 
                            allies={allies}
                            enemies={enemies}
                            neutrals={neutrals}
                            onMoveCharacter={moveCharacter}
                            onRemoveCharacter={removeCharacter}
                        />
                    </div>
                </div>

                <div className='ui-mainrow'>
                    {/* Logging area (below). FUTURE DASHBOARD HERE */}
                    {results && (
                        <div className="results">
                            <h3>Raw Results (debug)</h3>
                            <pre>{JSON.stringify(results, null, 2)}</pre>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default EveOracleUI;