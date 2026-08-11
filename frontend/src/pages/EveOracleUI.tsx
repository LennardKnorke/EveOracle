// frontend/src/pages/EveOracleUI/EveOracleUI.tsx

import React, { useEffect, useState } from 'react';
import TeamManagerWindow from "../components/TeamManager";
import MatchupDashboard from "../components/MatchupDashboard";
import "./EveOracleUI.css";
import { useAuth } from '../auth'
import { apiClient } from '../api/client';


export interface CharIdentifier {
    char_name: string;
    id: string|number;
    corporation_id: string|number;
    alliance_id: string|number;
};

export interface CharacterStats {
    char: CharIdentifier;
    stats: any; // Here the zkilldict is saved
};

function transformToCharacterStats(rawData: any): CharacterStats[] {
    if (!rawData) return [];
    const targetData = rawData.results !== undefined ? rawData.results : rawData;

    const mapSingleEntry = (entry: any): CharacterStats => {        
        const char: CharIdentifier = {
            char_name: entry.name || '',
            // Fallbacks handle camelCase or snake_case API conventions
            id: entry.id || 0,
            corporation_id: entry.corporationID || 0,
            alliance_id: entry.allianceID || 0,
        };

        return {
            char,
            stats: entry.stats || null
        };
    };

    // 2. If targetData is an Array, map over it directly
    if (Array.isArray(targetData)) {
        return targetData.map(mapSingleEntry);
    }

    // 3. If targetData is a Key/Value Dictionary object, iterate over its pairs
    if (typeof targetData === 'object' && targetData !== null) {
        return Object.entries(targetData).map(([_, value]: [string, any]) => {
            // Map the value object using our helper
            return mapSingleEntry(value);
        });
    }
    return [];
};

function EveOracleUI() {
    const { user } = useAuth();

    async function fetchUserFleet(id : string) {
        const fleet_team = await apiClient(`/char/currentFleet?char_id=${id}`);
        console.log(fleet_team);
    };
    async function fetchCharacters(names : string[]) {
        const data = await apiClient(`/char/stats`, {
            method : 'POST',
            body: JSON.stringify({char_names : names})
        });
        console.log(data);
    };

    useEffect(() => {
        fetchUserFleet(user?.id || "");
    });

    const [characterInput, setCharacterInput] = useState('');
    const [loading, setLoading] = useState(false);
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

        const lists = { allies, enemies, neutrals };
        const setLists = { allies: setAllies, enemies: setEnemies, neutrals: setNeutrals };

        const sourceList = lists[from].filter(char => char.char.id !== targetChar.char.id);
        const targetList = lists[to].some(char => char.char.id === targetChar.char.id)
            ? lists[to]
            : [...lists[to], targetChar];

        setLists[from](sourceList);
        setLists[to](targetList);
    };

    const removeCharacter = (
        from: 'allies' | 'enemies' | 'neutrals',
        targetChar: CharacterStats
    ) => {
        const lists = { allies, enemies, neutrals };
        const setLists = { allies: setAllies, enemies: setEnemies, neutrals: setNeutrals };
        const sourceList = lists[from].filter(char => char.char.id !== targetChar.char.id);
        setLists[from](sourceList);
    };

    const handleFetch = async () => {
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

        try {
            const rawData = await apiClient<number>('');
            const CharStats = transformToCharacterStats(rawData);

            const userCharName = localStorage.getItem('char_name');

            if (CharStats.length === 0) {
                setAllies([]);
                setEnemies([]);
                setNeutrals([]);
                return;
            }

            const userEntry = CharStats.find(
                (entry: CharacterStats) => entry.char.char_name?.toLowerCase() === userCharName?.toLowerCase()
            );

            let userAllianceId = null;
            if (userEntry && userEntry.char) {
                userAllianceId = userEntry.char.alliance_id || null;
            }

            if (!userAllianceId) {
                const fallbackNeutrals: CharacterStats[] = CharStats.filter(
                    (entry: CharacterStats) => entry.char?.char_name && entry.char?.id
                );
                setAllies([]);
                setEnemies([]);
                setNeutrals(fallbackNeutrals);
                return;
            }

            const alliesList: CharacterStats[] = [];
            const enemyList: CharacterStats[] = [];

            CharStats.forEach((entry: CharacterStats) => {
                const name = entry.char?.char_name || null;
                const id = entry.char?.id || null;
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
            setEnemies([]);
            setNeutrals([]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="eve-oracle-ui">
            <h2>EVE Oracle UI</h2>
            <div className="ui-layout">
                {/* Top Row: Input + Team Manager */}
                <div className="ui-toprow">
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
                    {/*
                    <div className="teammanager-area">
                        <TeamManagerWindow
                            allies={allies}
                            enemies={enemies}
                            neutrals={neutrals}
                            onMoveCharacter={moveCharacter}
                            onRemoveCharacter={removeCharacter}
                        />
                    </div>
                    */}
                </div>

                {/* Bottom Row: Matchup Dashboard */}
                <div className="ui-mainrow">
                    <MatchupDashboard allies={allies} enemies={enemies} />
                </div>
            </div>
        </div>
    );
}

export default EveOracleUI;