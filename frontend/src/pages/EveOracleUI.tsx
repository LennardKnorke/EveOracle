// frontend/src/pages/EveOracleUI.tsx

import React, { useState, useMemo } from 'react';
import LocalChatInputField from '../components/EveOracleUI/LocalChatCharacters';
import TeamManagerWindow from '../components/EveOracleUI/TeamManager';
import ShipSelectorModal from '../components/EveOracleUI/ShipSelectorModal';
import PilotSelectorModal from '../components/EveOracleUI/PilotSelectorModal';
import MatchupDashboard from '../components/EveOracleUI/MatchupDashboard';

import {
    type CharacterStats,
    type ShipInfo,
    type TeamToken,
    type ColumnKey,
    getCategoryByStanding,
    isW1,
    isW3,
} from '../api/type';
import { useAuth } from '../auth';
import { apiClient } from '../api/client';
import './EveOracleUI.css';

// Payload structure returned from backend (including optional ship info from fleet ESI)
interface BackendCharacterResponse extends CharacterStats {
    ship_id?: number | string | null;
    ship_name?: string | null;
    ship_class?: string | null;
}

export function EveOracleUI() {
    const { user } = useAuth();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [characterInputs, setCharacterInputs] = useState('');

    const [allies, setAllies] = useState<TeamToken[]>([]);
    const [neutrals, setNeutrals] = useState<TeamToken[]>([]);
    const [enemies, setEnemies] = useState<TeamToken[]>([]);

    // Modals State
    const [shipModalState, setShipModalState] = useState<{
        isOpen: boolean;
        targetToken?: TeamToken;
        targetColumn?: ColumnKey;
    }>({ isOpen: false });

    const [pilotModalState, setPilotModalState] = useState<{
        isOpen: boolean;
        targetW3Token?: TeamToken;
        targetColumn?: ColumnKey;
    }>({ isOpen: false });

    const existingCharIds = useMemo(() => {
        const ids = new Set<string>();
        [...allies, ...neutrals, ...enemies].forEach((t) => {
            if (t.character?.char_id) ids.add(String(t.character.char_id));
        });
        return ids;
    }, [allies, neutrals, enemies]);

    const existingCharNames = useMemo(() => {
        const names = new Set<string>();
        [...allies, ...neutrals, ...enemies].forEach((t) => {
            if (t.character?.char_name) names.add(t.character.char_name.toLowerCase());
        });
        return names;
    }, [allies, neutrals, enemies]);

    // Available unassigned W1 pilots across all columns
    const availableW1Pilots = useMemo(() => {
        const list: { token: TeamToken; column: ColumnKey }[] = [];
        allies.filter(isW1).forEach((t) => list.push({ token: t, column: 'allies' }));
        neutrals.filter(isW1).forEach((t) => list.push({ token: t, column: 'neutrals' }));
        enemies.filter(isW1).forEach((t) => list.push({ token: t, column: 'enemies' }));
        return list;
    }, [allies, neutrals, enemies]);

    /**
     * Dispatch fetched characters into W1 (or W2 if ship present) tokens
     */
    const distributeNewCharacters = (rawList: BackendCharacterResponse[], isFleet = false) => {
        const toAllies: TeamToken[] = [];
        const toNeutrals: TeamToken[] = [];
        const toEnemies: TeamToken[] = [];

        rawList.forEach((raw) => {
            if (existingCharIds.has(String(raw.char_id))) return;

            // Extract pure character stats
            const character: CharacterStats = {
                char_id: raw.char_id,
                char_name: raw.char_name,
                corporation_id: raw.corporation_id,
                alliance_id: raw.alliance_id,
                standing: raw.standing,
                stats: raw.stats,
            };

            // Extract pure ship info
            const ship: ShipInfo | null =
                raw.ship_id && raw.ship_name
                    ? {
                          id: raw.ship_id,
                          name: raw.ship_name,
                          shipClass: raw.ship_class || undefined,
                      }
                    : null;

            const token: TeamToken = {
                id: `token_${character.char_id}_${Date.now()}_${Math.random()}`,
                character,
                ship,
            };

            const category = getCategoryByStanding(character.standing, isFleet);
            if (category === 'allies') toAllies.push(token);
            else if (category === 'enemies') toEnemies.push(token);
            else toNeutrals.push(token);
        });

        if (toAllies.length > 0) setAllies((prev) => [...prev, ...toAllies]);
        if (toNeutrals.length > 0) setNeutrals((prev) => [...prev, ...toNeutrals]);
        if (toEnemies.length > 0) setEnemies((prev) => [...prev, ...toEnemies]);
    };

    /**
     * Option 1: Fetch Fleet (W2)
     */
    const handleFetchFleet = async () => {
        if (!user?.id) return;
        setLoading(true);
        setError(null);

        try {
            const data = await apiClient<BackendCharacterResponse[]>(
                `/char/currentFleet?char_id=${user.id}`
            );
            const fleetMembers = Array.isArray(data) ? data : Object.values(data);
            distributeNewCharacters(fleetMembers, true);
        } catch (err: any) {
            setError(err.message || 'Failed to fetch fleet members.');
        } finally {
            setLoading(false);
        }
    };

    /**
     * Option 2: Fetch Local Chat Pilots (W1)
     */
    const handleFetchCharacters = async () => {
        const namesArray = characterInputs
            .split('\n')
            .map((name) => name.trim())
            .filter((name) => name.length > 0 && !existingCharNames.has(name.toLowerCase()));

        if (namesArray.length === 0) {
            setError(characterInputs.trim() ? 'All entered pilots are already loaded.' : 'Please enter pilot names.');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const payload = {
                char_names: namesArray,
                existing_char_ids: Array.from(existingCharIds),
            };

            const data = await apiClient<BackendCharacterResponse[]>('/char/stats', {
                method: 'POST',
                body: JSON.stringify(payload),
            });

            const newCharacters = Array.isArray(data) ? data : Object.values(data);
            distributeNewCharacters(newCharacters, false);
            setCharacterInputs('');
        } catch (err: any) {
            setError(err.message || 'Failed to fetch character stats.');
        } finally {
            setLoading(false);
        }
    };

    /**
     * Remove All (keep logged in user)
     */
    const handleRemoveAll = () => {
        if (!user?.id) {
            setAllies([]);
            setNeutrals([]);
            setEnemies([]);
            return;
        }

        const isUserToken = (t: TeamToken) => String(t.character?.char_id) === String(user.id);
        setAllies((prev) => prev.filter(isUserToken));
        setNeutrals((prev) => prev.filter(isUserToken));
        setEnemies((prev) => prev.filter(isUserToken));
    };

    /**
     * Move token between columns
     */
    const handleMoveToken = (from: ColumnKey, to: ColumnKey, token: TeamToken) => {
        if (from === to) return;

        const removeFilter = (list: TeamToken[]) => list.filter((t) => t.id !== token.id);
        if (from === 'allies') setAllies(removeFilter);
        else if (from === 'neutrals') setNeutrals(removeFilter);
        else if (from === 'enemies') setEnemies(removeFilter);

        if (to === 'allies') setAllies((prev) => [...prev, token]);
        else if (to === 'neutrals') setNeutrals((prev) => [...prev, token]);
        else if (to === 'enemies') setEnemies((prev) => [...prev, token]);
    };

    /**
     * Merge W1 and W3 into W2. Stays in W1's column.
     */
    const handleMergeTokens = (
        draggedToken: TeamToken,
        fromCol: ColumnKey,
        targetToken: TeamToken,
        toCol: ColumnKey
    ) => {
        const w1 = isW1(draggedToken) ? draggedToken : targetToken;
        const w3 = isW3(draggedToken) ? draggedToken : targetToken;
        const w1Col = isW1(draggedToken) ? fromCol : toCol;

        const mergedW2: TeamToken = {
            id: w1.id,
            character: w1.character,
            ship: w3.ship,
        };

        const clean = (list: TeamToken[]) =>
            list.filter((t) => t.id !== draggedToken.id && t.id !== targetToken.id);

        setAllies(clean);
        setNeutrals(clean);
        setEnemies(clean);

        if (w1Col === 'allies') setAllies((prev) => [...clean(prev), mergedW2]);
        else if (w1Col === 'neutrals') setNeutrals((prev) => [...clean(prev), mergedW2]);
        else if (w1Col === 'enemies') setEnemies((prev) => [...clean(prev), mergedW2]);
    };

    const handleRemoveToken = (from: ColumnKey, token: TeamToken) => {
        const filter = (list: TeamToken[]) => list.filter((t) => t.id !== token.id);
        if (from === 'allies') setAllies(filter);
        else if (from === 'neutrals') setNeutrals(filter);
        else if (from === 'enemies') setEnemies(filter);
    };

    const handleOpenAddShipModal = (column: ColumnKey) => {
        setShipModalState({ isOpen: true, targetColumn: column });
    };

    const handleOpenAssignShipModal = (token: TeamToken, column: ColumnKey) => {
        setShipModalState({ isOpen: true, targetToken: token, targetColumn: column });
    };

    const handleShipSelected = (ship: ShipInfo) => {
        const { targetToken, targetColumn } = shipModalState;

        if (targetToken && targetColumn) {
            const updatedToken: TeamToken = { ...targetToken, ship };
            const updateList = (list: TeamToken[]) =>
                list.map((t) => (t.id === targetToken.id ? updatedToken : t));

            if (targetColumn === 'allies') setAllies(updateList);
            else if (targetColumn === 'neutrals') setNeutrals(updateList);
            else if (targetColumn === 'enemies') setEnemies(updateList);
        } else if (targetColumn) {
            const newW3: TeamToken = {
                id: `ship_${ship.id}_${Date.now()}_${Math.random()}`,
                character: null,
                ship,
            };

            if (targetColumn === 'allies') setAllies((prev) => [...prev, newW3]);
            else if (targetColumn === 'neutrals') setNeutrals((prev) => [...prev, newW3]);
            else if (targetColumn === 'enemies') setEnemies((prev) => [...prev, newW3]);
        }

        setShipModalState({ isOpen: false });
    };

    const handleOpenAssignPilotModal = (w3Token: TeamToken, column: ColumnKey) => {
        setPilotModalState({ isOpen: true, targetW3Token: w3Token, targetColumn: column });
    };

    const handlePilotSelected = (pilotToken: TeamToken) => {
        const { targetW3Token } = pilotModalState;
        if (!targetW3Token) return;

        let pilotCol: ColumnKey = 'allies';
        if (neutrals.some((t) => t.id === pilotToken.id)) pilotCol = 'neutrals';
        else if (enemies.some((t) => t.id === pilotToken.id)) pilotCol = 'enemies';

        handleMergeTokens(pilotToken, pilotCol, targetW3Token, pilotModalState.targetColumn || 'neutrals');
        setPilotModalState({ isOpen: false });
    };

    const handleDetachShip = (token: TeamToken, column: ColumnKey) => {
        const updatedToken: TeamToken = { ...token, ship: null };
        const updateList = (list: TeamToken[]) =>
            list.map((t) => (t.id === token.id ? updatedToken : t));

        if (column === 'allies') setAllies(updateList);
        else if (column === 'neutrals') setNeutrals(updateList);
        else if (column === 'enemies') setEnemies(updateList);
    };

    return (
        <div className="eve-oracle-ui">
            <header className="ui-header">
                <h2>Tactical Overview</h2>
                <span className="pilot-badge">Pilot: {user?.char_name || 'Unknown'}</span>
            </header>

            {error && <div className="error-banner">{error}</div>}

            <div className="ui-layout">
                {/* Top Section */}
                <section className="ui-input-section">
                    <div className="input-box-wrapper">
                        <LocalChatInputField
                            value={characterInputs}
                            onChange={setCharacterInputs}
                            disabled={loading}
                        />
                    </div>

                    <div className="actions-panel">
                        <button
                            type="button"
                            className="btn btn-primary"
                            onClick={handleFetchCharacters}
                            disabled={loading}
                        >
                            {loading ? 'Fetching...' : 'Fetch Characters'}
                        </button>
                        <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={handleFetchFleet}
                            disabled={loading}
                        >
                            {loading ? 'Updating Fleet...' : 'Update Fleet'}
                        </button>
                        <button
                            type="button"
                            className="btn btn-danger"
                            onClick={handleRemoveAll}
                            disabled={loading}
                        >
                            Remove All
                        </button>
                    </div>
                </section>

                {/* Middle Section: 3 Columns */}
                <section className="ui-teams-section">
                    <TeamManagerWindow
                        allies={allies}
                        neutrals={neutrals}
                        enemies={enemies}
                        onMoveToken={handleMoveToken}
                        onMergeTokens={handleMergeTokens}
                        onRemoveToken={handleRemoveToken}
                        onAddShipClick={handleOpenAddShipModal}
                        onClickPilotToken={handleOpenAssignPilotModal}
                        onClickShipToken={handleOpenAssignShipModal}
                        onDetachShip={handleDetachShip}
                    />
                </section>

                <section className="ui-matchup-section" style={{ width: '100%' }}>
                    <MatchupDashboard allies={allies} enemies={enemies} />
                </section>
            </div>

            {/* Modals */}
            <ShipSelectorModal
                isOpen={shipModalState.isOpen}
                onSelect={handleShipSelected}
                onClose={() => setShipModalState({ isOpen: false })}
            />

            <PilotSelectorModal
                isOpen={pilotModalState.isOpen}
                availablePilots={availableW1Pilots}
                onSelect={handlePilotSelected}
                onClose={() => setPilotModalState({ isOpen: false })}
            />
        </div>
    );
}

export default EveOracleUI;