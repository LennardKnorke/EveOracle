// frontend/src/components/MatchupDashboard.tsx

import React, { useState, useEffect } from 'react';
import { type CharacterStats } from '../api/zkill';
import { getShipName, getShipData } from '../api/ships';
import './MatchupDashboard.css';

// Helper: format large numbers with "K", "M", "B", "T" suffixes
function formatISK(value: number): string {
    if (!value) return '0';
    const abs = Math.abs(value);
    if (abs >= 1e12) return (value / 1e12).toFixed(1) + 'T';
    if (abs >= 1e9) return (value / 1e9).toFixed(1) + 'B';
    if (abs >= 1e6) return (value / 1e6).toFixed(1) + 'M';
    if (abs >= 1e3) return (value / 1e3).toFixed(1) + 'K';
    return value.toString();
}

function formatNumber(num: number): string {
    if (!num) return '0';
    return num.toLocaleString();
}

// Helper: Get stats for the last week (from rankHistory.weekly or months)
function getLastWeekStats(stats: any) {
    // Try to get from rankHistory.weekly.all
    const weekly = stats?.rankHistory?.weekly?.all;
    if (weekly) {
        const entries = Object.entries(weekly);
        if (entries.length > 0) {
            const latest = entries[entries.length - 1][1] as any;
            const metrics = latest?.metrics || {};
            return {
                shipsDestroyed: metrics.shipsDestroyed || 0,
                shipsLost: metrics.shipsLost || 0,
                iskDestroyed: metrics.iskDestroyed || 0,
                iskLost: metrics.iskLost || 0,
            };
        }
    }

    // Fallback: get the most recent month from months
    const months = stats?.months;
    if (months) {
        const entries = Object.entries(months);
        if (entries.length > 0) {
            const latest = entries[entries.length - 1][1] as any;
            return {
                shipsDestroyed: latest.shipsDestroyed || 0,
                shipsLost: latest.shipsLost || 0,
                iskDestroyed: latest.iskDestroyed || 0,
                iskLost: latest.iskLost || 0,
            };
        }
    }

    return { shipsDestroyed: 0, shipsLost: 0, iskDestroyed: 0, iskLost: 0 };
}

// Helper: Get top ship type (most kills) from stats
function getTopShip(stats: any): string {
    const topAllTime = stats?.topAllTime || [];
    const shipData = topAllTime.find((item: any) => item.type === 'ship');
    if (shipData?.data?.length > 0) {
        // Return the ship type ID as a string for now; we could resolve names with a map later
        return `Ship ID: ${shipData.data[0].shipTypeID}`;
    }
    return '—';
}

interface PlayerSmallCardProps {
    character: CharacterStats;
    onClick: () => void;
    isExpanded: boolean;
}

export function PlayerSmallCard({ character, onClick, isExpanded }: PlayerSmallCardProps) {
    const stats = character.stats || {};
    const weekly = getLastWeekStats(stats);
    const avgGangSize = stats.avgGangSize || 0;

    const portraitUrl = `https://images.evetech.net/characters/${character.char.id}/portrait?size=64`;
    const corpLogoUrl = `https://images.evetech.net/corporations/${character.char.corporation_id}/logo?size=32`;
    const allianceLogoUrl = character.char.alliance_id
        ? `https://images.evetech.net/alliances/${character.char.alliance_id}/logo?size=32`
        : undefined;

    return (
        <div className={`player-small-card ${isExpanded ? 'expanded' : ''}`} onClick={onClick}>
            <div className="card-icons">
                <img src={portraitUrl} alt={character.char.char_name} className="portrait" loading="lazy" />
                <div className="corp-alliance-icons">
                    <img src={corpLogoUrl} alt="Corporation" className="corp-icon" loading="lazy" />
                    {allianceLogoUrl && (
                        <img src={allianceLogoUrl} alt="Alliance" className="alliance-icon" loading="lazy" />
                    )}
                </div>
            </div>
            <div className="card-info">
                <div className="card-name">{character.char.char_name}</div>
                <div className="card-stats">
                    <span className="stat-item">
                        <span className="stat-label">K/D (W):</span>
                        <span className="stat-value kills">{formatNumber(weekly.shipsDestroyed)}</span>
                        <span className="stat-separator">/</span>
                        <span className="stat-value losses">{formatNumber(weekly.shipsLost)}</span>
                    </span>
                    <span className="stat-item">
                        <span className="stat-label">ISK (W):</span>
                        <span className="stat-value isk-kills">{formatISK(weekly.iskDestroyed)}</span>
                        <span className="stat-separator">/</span>
                        <span className="stat-value isk-losses">{formatISK(weekly.iskLost)}</span>
                    </span>
                    <span className="stat-item">
                        <span className="stat-label">Avg Gang:</span>
                        <span className="stat-value">{avgGangSize.toFixed(1)}</span>
                    </span>
                </div>
            </div>
        </div>
    );
}

interface LargePlayerCardProps {
    character: CharacterStats;
    onClose: () => void;
}

export function LargePlayerCard({ character, onClose }: LargePlayerCardProps) {
    const stats = character.stats || {};
    const weekly = getLastWeekStats(stats);
    const [topShips, setTopShips] = useState<Array<{ id: number; kills: number; name: string }>>([]);
    const [topSystems, setTopSystems] = useState<Array<{ id: number; kills: number }>>([]);
    const [monthEntries, setMonthEntries] = useState<Array<[string, any]>>([]);
    
    useEffect(() => {
        // Extract top ships and resolve names
        const topAllTime = stats?.topAllTime || [];
        const shipData = topAllTime.find((item: any) => item.type === 'ship');
        const rawShips = shipData?.data?.slice(0, 5) || [];

        Promise.all(
            rawShips.map(async (ship: any) => {
                const name = await getShipName(ship.shipTypeID);
                return { id: ship.shipTypeID, kills: ship.kills, name };
            })
        ).then(setTopShips);

        // Systems (no name resolution needed for now)
        const systemData = topAllTime.find((item: any) => item.type === 'system');
        setTopSystems(systemData?.data?.slice(0, 5) || []);

        // Months
        const months = stats?.months || {};
        setMonthEntries(Object.entries(months).slice(-3).reverse());
    }, [stats]);

    return (
        <div className="large-player-card">
            <button className="close-button" onClick={onClose}>✕</button>
            <div className="large-card-header">
                <img
                    src={`https://images.evetech.net/characters/${character.char.id}/portrait?size=128`}
                    alt={character.char.char_name}
                    className="large-portrait"
                />
                <div className="large-header-info">
                    <h2>{character.char.char_name}</h2>
                    <p>Corporation: {character.char.corporation_id}</p>
                    {character.char.alliance_id && (
                        <p>Alliance: {character.char.alliance_id}</p>
                    )}
                </div>
            </div>

            <div className="large-stats-grid">
                <div className="stat-group">
                    <h4>All-Time</h4>
                    <div className="stat-row">
                        <span>Kills: <strong>{formatNumber(stats.shipsDestroyed || 0)}</strong></span>
                        <span>Losses: <strong>{formatNumber(stats.shipsLost || 0)}</strong></span>
                    </div>
                    <div className="stat-row">
                        <span>ISK Destroyed: <strong>{formatISK(stats.iskDestroyed || 0)}</strong></span>
                        <span>ISK Lost: <strong>{formatISK(stats.iskLost || 0)}</strong></span>
                    </div>
                    <div className="stat-row">
                        <span>Solo Kills: <strong>{formatNumber(stats.soloKills || 0)}</strong></span>
                        <span>Solo Losses: <strong>{formatNumber(stats.soloLosses || 0)}</strong></span>
                    </div>
                    <div className="stat-row">
                        <span>Avg Gang Size: <strong>{(stats.avgGangSize || 0).toFixed(1)}</strong></span>
                        <span>Danger Ratio: <strong>{stats.dangerRatio || 0}</strong></span>
                    </div>
                </div>

                <div className="stat-group">
                    <h4>Last Week</h4>
                    <div className="stat-row">
                        <span>Kills: <strong>{formatNumber(weekly.shipsDestroyed)}</strong></span>
                        <span>Losses: <strong>{formatNumber(weekly.shipsLost)}</strong></span>
                    </div>
                    <div className="stat-row">
                        <span>ISK Destroyed: <strong>{formatISK(weekly.iskDestroyed)}</strong></span>
                        <span>ISK Lost: <strong>{formatISK(weekly.iskLost)}</strong></span>
                    </div>
                </div>
            </div>

            <div className="large-top-lists">
                <div className="top-list">
                    <h4>Top Ships</h4>
                    <ul>
                        {topShips.map((ship) => (
                            <li key={ship.id}>
                                {ship.name} — {ship.kills} kills
                            </li>
                        ))}
                        {topShips.length === 0 && <li>No data</li>}
                    </ul>
                </div>
                <div className="top-list">
                    <h4>Top Systems</h4>
                    <ul>
                        {topSystems.map((system: any) => (
                            <li key={system.solarSystemID}>
                                System {system.solarSystemID} — {system.kills} kills
                            </li>
                        ))}
                        {topSystems.length === 0 && <li>No data</li>}
                    </ul>
                </div>
                <div className="top-list">
                    <h4>Recent Months</h4>
                    <ul>
                        {monthEntries.map(([month, data]: [string, any]) => (
                            <li key={month}>
                                {month}: {data.shipsDestroyed || 0}K / {data.shipsLost || 0}L
                            </li>
                        ))}
                        {monthEntries.length === 0 && <li>No data</li>}
                    </ul>
                </div>
            </div>
        </div>
    );
}

interface MatchupDashboardProps {
    allies: CharacterStats[];
    enemies: CharacterStats[];
}

export function MatchupDashboard({ allies, enemies }: MatchupDashboardProps) {
    // Track which character is expanded in each column (by id)
    const [expandedAllies, setExpandedAllies] = useState<Set<number>>(new Set());
    const [expandedEnemies, setExpandedEnemies] = useState<Set<number>>(new Set());

    const toggleExpand = (charId: number, column: 'allies' | 'enemies') => {
        if (column === 'allies') {
            const newSet = new Set(expandedAllies);
            if (newSet.has(charId)) {
                newSet.delete(charId);
            } else {
                newSet.add(charId);
            }
            setExpandedAllies(newSet);
        } else {
            const newSet = new Set(expandedEnemies);
            if (newSet.has(charId)) {
                newSet.delete(charId);
            } else {
                newSet.add(charId);
            }
            setExpandedEnemies(newSet);
        }
    };

    const renderColumn = (items: CharacterStats[], column: 'allies' | 'enemies', expandedSet: Set<number>) => {
        if (items.length === 0) {
            return (
                <div className="dashboard-column empty">
                    <p>No characters in this column.</p>
                </div>
            );
        }

        // If exactly one item is expanded, show the LargePlayerCard for that item
        const expandedItem = items.find(item => expandedSet.has(item.char.id as number));
        if (expandedItem) {
            return (
                <div className="dashboard-column expanded">
                    <LargePlayerCard
                        character={expandedItem}
                        onClose={() => toggleExpand(expandedItem.char.id as number, column)}
                    />
                </div>
            );
        }

        // Otherwise, show the list of small cards
        return (
            <div className="dashboard-column list">
                <div className="column-scroll">
                    {items.map((char) => (
                        <PlayerSmallCard
                            key={char.char.id}
                            character={char}
                            onClick={() => toggleExpand(char.char.id as number, column)}
                            isExpanded={false}
                        />
                    ))}
                </div>
            </div>
        );
    };

    return (
        <div className="matchup-dashboard">
            <div className="dashboard-columns">
                <div className="column-wrapper allies-column">
                    <h3>Allies ({allies.length})</h3>
                    {renderColumn(allies, 'allies', expandedAllies)}
                </div>
                <div className="column-wrapper enemies-column">
                    <h3>Enemies ({enemies.length})</h3>
                    {renderColumn(enemies, 'enemies', expandedEnemies)}
                </div>
            </div>
        </div>
    );
}

export default MatchupDashboard;