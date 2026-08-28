// frontend/src/components/MatchupDashboard/MatchupDashboard.tsx

import React, { useState, useEffect, useMemo } from 'react';
import { type TeamToken, isW1, isW2, isW3 } from '../../api/type';
import FleetCompositionSummary from './FleetCompositionSummary';
import { getShipsDatabase } from '../../api/ships';
import './MatchupDashboard.css';

// -------------------------------------------------------------------------
// Helpers
// -------------------------------------------------------------------------
function formatISK(value?: number): string {
    if (!value) return '0 ISK';
    const abs = Math.abs(value);
    if (abs >= 1e12) return (value / 1e12).toFixed(2) + 'T ISK';
    if (abs >= 1e9) return (value / 1e9).toFixed(2) + 'B ISK';
    if (abs >= 1e6) return (value / 1e6).toFixed(1) + 'M ISK';
    if (abs >= 1e3) return (value / 1e3).toFixed(0) + 'K ISK';
    return value.toLocaleString() + ' ISK';
}

function formatNumber(num?: number): string {
    if (!num && num !== 0) return '0';
    return num.toLocaleString();
}

function getWeeklyMetrics(stats: any) {
    const weeklyMetrics = stats?.rankings?.weekly?.all?.metrics;
    if (weeklyMetrics) {
        return {
            shipsDestroyed: weeklyMetrics.shipsDestroyed || 0,
            shipsLost: weeklyMetrics.shipsLost || 0,
            iskDestroyed: weeklyMetrics.iskDestroyed || 0,
            iskLost: weeklyMetrics.iskLost || 0,
        };
    }
    const weeklyObj = stats?.rankHistory?.weekly?.all;
    if (weeklyObj) {
        const entries = Object.values(weeklyObj);
        if (entries.length > 0) {
            const latest = entries[entries.length - 1] as any;
            return {
                shipsDestroyed: latest?.metrics?.shipsDestroyed || 0,
                shipsLost: latest?.metrics?.shipsLost || 0,
                iskDestroyed: latest?.metrics?.iskDestroyed || 0,
                iskLost: latest?.metrics?.iskLost || 0,
            };
        }
    }
    return { shipsDestroyed: 0, shipsLost: 0, iskDestroyed: 0, iskLost: 0 };
}

function getShipExperience(stats: any, shipId?: number | string | null) {
    if (!shipId || !stats) return null;
    const sId = Number(shipId);
    const topShips = stats.topShips || [];
    const recentShips = stats.recentShips || [];

    const found =
        topShips.find((s: any) => s.shipTypeID === sId) ||
        recentShips.find((s: any) => s.shipTypeID === sId);

    if (found) {
        return {
            kills: found.kills || 0,
            losses: found.losses || 0,
            appearances: found.appearances || 0,
            isk: found.isk || 0,
        };
    }
    return { kills: 0, losses: 0, appearances: 0, isk: 0 };
}

// -------------------------------------------------------------------------
// Small Compact Card (W1, W2, W3)
// -------------------------------------------------------------------------
interface PlayerSmallCardProps {
    token: TeamToken;
    onClick: () => void;
}

export function PlayerSmallCard({ token, onClick }: PlayerSmallCardProps) {
    const { character, ship } = token;

    // W3: Ship Only
    if (isW3(token) && ship) {
        return (
            <div className="player-small-card card-w3" onClick={onClick}>
                <div className="card-icons">
                    <img
                        src={`https://images.evetech.net/types/${ship.id}/icon?size=32`}
                        alt={ship.name}
                        className="card-ship-icon"
                    />
                </div>
                <div className="card-info">
                    <div className="card-name card-ship-name">{ship.name}</div>
                    <div className="card-sub">{ship.shipClass || 'Unidentified Class'} • [Spotted Ship]</div>
                </div>
            </div>
        );
    }

    const stats = character?.stats || {};
    const weekly = getWeeklyMetrics(stats);
    const danger = stats.dangerRatio ?? 0;
    const avgGang = stats.avgGangSize ?? 0;
    const shipExp = getShipExperience(stats, ship?.id);

    return (
        <div className={`player-small-card ${isW2(token) ? 'card-w2' : 'card-w1'}`} onClick={onClick}>
            {/* Icons */}
            <div className="card-icons">
                <img
                    src={`https://images.evetech.net/characters/${character?.char_id}/portrait?size=64`}
                    alt={character?.char_name}
                    className="card-portrait"
                    loading="lazy"
                />
                <div className="card-secondary-icons">
                    {ship ? (
                        <img
                            src={`https://images.evetech.net/types/${ship.id}/icon?size=32`}
                            alt={ship.name}
                            className="card-ship-badge"
                            title={ship.name}
                        />
                    ) : (
                        character?.corporation_id && (
                            <img
                                src={`https://images.evetech.net/corporations/${character.corporation_id}/logo?size=32`}
                                alt="Corp"
                                className="card-corp-badge"
                            />
                        )
                    )}
                </div>
            </div>

            {/* Pilot / Ship Info */}
            <div className="card-info">
                <div className="card-header-row">
                    <span className="card-name">{character?.char_name}</span>
                    <span
                        className={`danger-tag ${
                            danger >= 60 ? 'danger-high' : danger >= 30 ? 'danger-med' : 'danger-low'
                        }`}
                    >
                        {danger}% Danger
                    </span>
                </div>

                <div className="card-stats-row">
                    <span className="stat-segment">
                        <span className="stat-label">W:</span>
                        <span className="stat-val kills">{weekly.shipsDestroyed}K</span> /
                        <span className="stat-val losses">{weekly.shipsLost}L</span>
                    </span>

                    <span className="stat-segment">
                        <span className="stat-label">Gang:</span>
                        <span className="stat-val">{avgGang.toFixed(0)}</span>
                    </span>

                    {ship ? (
                        <span className="stat-segment ship-tag">
                            <span className="stat-label">{ship.name}:</span>
                            <span className="stat-val">{shipExp ? `${shipExp.kills}k` : '0k'}</span>
                        </span>
                    ) : (
                        <span className="stat-segment isk-tag">
                            <span className="stat-val">{formatISK(stats.iskDestroyed || 0)}</span>
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}

// -------------------------------------------------------------------------
// Large Expanded Card for Pilots (W1 & W2)
// -------------------------------------------------------------------------
interface LargePlayerCardProps {
    token: TeamToken;
    onClose: () => void;
}

export function LargePlayerCard({ token, onClose }: LargePlayerCardProps) {
    const { character, ship } = token;
    const stats = character?.stats || {};
    const weekly = getWeeklyMetrics(stats);
    const recentMetrics = stats?.rankings?.recent?.all?.metrics || {};
    const shipExp = getShipExperience(stats, ship?.id);

    const [shipsDb, setShipsDb] = useState<Record<string, any>>({});

    useEffect(() => {
        getShipsDatabase().then(setShipsDb);
    }, []);

    // Top Ships
    const topShipsList = useMemo(() => {
        const list = stats.topShips || [];
        return list.slice(0, 5).map((s: any) => ({
            id: s.shipTypeID,
            name: shipsDb[String(s.shipTypeID)]?.name || `Ship ${s.shipTypeID}`,
            kills: s.kills || 0,
            losses: s.losses || 0,
            isk: s.isk || 0,
        }));
    }, [stats, shipsDb]);

    // Top Systems
    const topSystemsList = useMemo(() => {
        const topLists = stats.topLists || [];
        const systems = topLists.find((t: any) => t.type === 'solarSystem')?.values || [];
        if (systems.length > 0) return systems.slice(0, 4);

        const topAllTime = stats.topAllTime || [];
        const allTimeSys = topAllTime.find((t: any) => t.type === 'system')?.data || [];
        return allTimeSys.slice(0, 4).map((s: any) => ({
            solarSystemName: `System ${s.solarSystemID}`,
            kills: s.kills,
        }));
    }, [stats]);

    return (
        <div className="large-player-card">
            <button className="close-expanded-btn" onClick={onClose} title="Collapse to list">✕</button>

            {/* Header / Identity */}
            <div className="large-header">
                <img
                    src={`https://images.evetech.net/characters/${character?.char_id}/portrait?size=128`}
                    alt={character?.char_name}
                    className="large-portrait"
                />
                <div className="large-identity">
                    <h2>{character?.char_name}</h2>
                    <div className="large-badges">
                        {character?.corporation_id && (
                            <span className="corp-badge">Corp: {character.corporation_id}</span>
                        )}
                        {character?.alliance_id && (
                            <span className="alliance-badge">Alliance: {character.alliance_id}</span>
                        )}
                        {stats?.info?.security_status !== undefined && (
                            <span className="sec-status-badge">Sec: {stats.info.security_status.toFixed(1)}</span>
                        )}
                    </div>
                </div>
            </div>

            {/* Active Ship Dossier (W2) */}
            {ship && (
                <div className="active-ship-dossier">
                    <div className="dossier-header">
                        <img
                            src={`https://images.evetech.net/types/${ship.id}/icon?size=32`}
                            alt={ship.name}
                            className="dossier-ship-icon"
                        />
                        <div>
                            <h4>Active Ship: {ship.name}</h4>
                            <span className="dossier-class">{ship.shipClass || 'Combat Vessel'}</span>
                        </div>
                    </div>
                    <div className="dossier-stats-grid">
                        <div>Kills in Hull: <strong>{shipExp?.kills ?? 0}</strong></div>
                        <div>Losses: <strong>{shipExp?.losses ?? 0}</strong></div>
                        <div>Hull ISK Destroyed: <strong>{formatISK(shipExp?.isk || 0)}</strong></div>
                    </div>
                </div>
            )}

            {/* Combat Metrics Grid */}
            <div className="metrics-grid">
                {/* All-Time */}
                <div className="metric-box">
                    <h5>All-Time Record</h5>
                    <div className="metric-row"><span>Kills / Losses:</span> <strong>{formatNumber(stats.shipsDestroyed)} / {formatNumber(stats.shipsLost)}</strong></div>
                    <div className="metric-row"><span>ISK Destroyed:</span> <strong className="green">{formatISK(stats.iskDestroyed)}</strong></div>
                    <div className="metric-row"><span>ISK Lost:</span> <strong className="red">{formatISK(stats.iskLost)}</strong></div>
                    <div className="metric-row"><span>Solo K / L:</span> <strong>{formatNumber(stats.soloKills)} / {formatNumber(stats.soloLosses)}</strong></div>
                    <div className="metric-row"><span>Danger Rating:</span> <strong>{stats.dangerRatio || 0}%</strong></div>
                    <div className="metric-row"><span>Avg Gang Size:</span> <strong>{(stats.avgGangSize || 0).toFixed(1)}</strong></div>
                </div>

                {/* Recent / Weekly */}
                <div className="metric-box">
                    <h5>Recent & Weekly</h5>
                    <div className="metric-row"><span>Weekly Kills:</span> <strong>{weekly.shipsDestroyed}</strong></div>
                    <div className="metric-row"><span>Weekly Losses:</span> <strong>{weekly.shipsLost}</strong></div>
                    <div className="metric-row"><span>Weekly ISK:</span> <strong className="green">{formatISK(weekly.iskDestroyed)}</strong></div>
                    <div className="metric-row"><span>Last 30d Kills:</span> <strong>{recentMetrics.shipsDestroyed || 0}</strong></div>
                    <div className="metric-row"><span>Last 30d Losses:</span> <strong>{recentMetrics.shipsLost || 0}</strong></div>
                    <div className="metric-row"><span>Last 30d ISK:</span> <strong className="green">{formatISK(recentMetrics.iskDestroyed || 0)}</strong></div>
                </div>
            </div>

            {/* Top Ships Flown */}
            <div className="top-lists-section">
                <div className="top-list-block">
                    <h5>Top Ships Flown</h5>
                    <ul>
                        {topShipsList.map((s) => (
                            <li key={s.id}>
                                <img
                                    src={`https://images.evetech.net/types/${s.id}/icon?size=32`}
                                    alt={s.name}
                                    className="list-ship-icon"
                                    onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
                                />
                                <div className="list-ship-info">
                                    <span>{s.name}</span>
                                    <small>{s.kills} Kills ({formatISK(s.isk)})</small>
                                </div>
                            </li>
                        ))}
                        {topShipsList.length === 0 && <li>No ship history available</li>}
                    </ul>
                </div>

                {/* Top Systems */}
                <div className="top-list-block">
                    <h5>Frequent Systems</h5>
                    <ul>
                        {topSystemsList.map((sys: any, idx: number) => (
                            <li key={idx}>
                                <span className="sys-name">📍 {sys.solarSystemName || `System ${sys.solarSystemID}`}</span>
                                <small>{sys.kills} kills</small>
                            </li>
                        ))}
                        {topSystemsList.length === 0 && <li>No system activity recorded</li>}
                    </ul>
                </div>
            </div>
        </div>
    );
}

// -------------------------------------------------------------------------
// Large Card for W3 (Ship Only)
// -------------------------------------------------------------------------
export function LargeShipCard({ token, onClose }: { token: TeamToken; onClose: () => void }) {
    const { ship } = token;
    return (
        <div className="large-player-card large-ship-only-card">
            <button className="close-expanded-btn" onClick={onClose}>✕</button>
            <div className="large-header">
                <img
                    src={`https://images.evetech.net/types/${ship?.id}/icon?size=64`}
                    alt={ship?.name}
                    className="large-ship-img"
                />
                <div className="large-identity">
                    <h2>{ship?.name}</h2>
                    <div className="large-badges">
                        <span className="ship-class-badge">{ship?.shipClass || 'Combat Ship'}</span>
                        {ship?.faction && <span className="faction-badge">{ship.faction}</span>}
                    </div>
                </div>
            </div>
            <p className="ship-only-note">
                Spotted ship with no assigned pilot. Link a pilot to view killboard combat telemetry.
            </p>
        </div>
    );
}

// -------------------------------------------------------------------------
// Main Matchup Dashboard Container
// -------------------------------------------------------------------------
interface MatchupDashboardProps {
    allies: TeamToken[];
    enemies: TeamToken[];
}

export function MatchupDashboard({ allies, enemies }: MatchupDashboardProps) {
    const [expandedAllyId, setExpandedAllyId] = useState<string | null>(null);
    const [expandedEnemyId, setExpandedEnemyId] = useState<string | null>(null);

    // Filter by shipClass per column
    const [allyClassFilter, setAllyClassFilter] = useState<string | null>(null);
    const [enemyClassFilter, setEnemyClassFilter] = useState<string | null>(null);

    const toggleAlly = (id: string) => {
        setExpandedAllyId((prev) => (prev === id ? null : id));
    };

    const toggleEnemy = (id: string) => {
        setExpandedEnemyId((prev) => (prev === id ? null : id));
    };

    const filterTokens = (tokens: TeamToken[], classFilter: string | null) => {
        if (!classFilter) return tokens;
        if (classFilter === 'Unknown') {
            return tokens.filter(isW1);
        }
        return tokens.filter((t) => t.ship && t.ship.shipClass === classFilter);
    };

    const filteredAllies = useMemo(() => filterTokens(allies, allyClassFilter), [allies, allyClassFilter]);
    const filteredEnemies = useMemo(() => filterTokens(enemies, enemyClassFilter), [enemies, enemyClassFilter]);

    const renderColumn = (
        tokens: TeamToken[],
        filteredList: TeamToken[],
        expandedId: string | null,
        classFilter: string | null,
        onSetClassFilter: (shipClass: string | null) => void,
        onToggle: (id: string) => void,
        onClose: () => void
    ) => {
        if (tokens.length === 0) {
            return (
                <div className="dashboard-column empty">
                    <p>No pilots or ships in this column.</p>
                </div>
            );
        }

        const expandedToken = tokens.find((t) => t.id === expandedId);
        if (expandedToken) {
            return (
                <div className="dashboard-column expanded">
                    {isW3(expandedToken) ? (
                        <LargeShipCard token={expandedToken} onClose={onClose} />
                    ) : (
                        <LargePlayerCard token={expandedToken} onClose={onClose} />
                    )}
                </div>
            );
        }

        return (
            <div className="dashboard-column list">
                {/* Fleet Composition Summary by shipClass */}
                <FleetCompositionSummary
                    tokens={tokens}
                    selectedShipClass={classFilter}
                    onSelectShipClass={onSetClassFilter}
                />

                {/* Filtered Cards List */}
                <div className="column-scroll">
                    {filteredList.map((token) => (
                        <PlayerSmallCard
                            key={token.id}
                            token={token}
                            onClick={() => onToggle(token.id)}
                        />
                    ))}
                    {filteredList.length === 0 && (
                        <div className="dashboard-column empty">
                            <p>No pilots match this ship class filter.</p>
                        </div>
                    )}
                </div>
            </div>
        );
    };

    return (
        <div className="matchup-dashboard">
            <div className="dashboard-columns">
                {/* Allies Column */}
                <div className="column-wrapper allies-column">
                    <div className="column-top-bar allies-bar">
                        <h3>Allies ({allies.length})</h3>
                        {expandedAllyId && (
                            <button className="back-btn" onClick={() => setExpandedAllyId(null)}>← Back to list</button>
                        )}
                    </div>
                    {renderColumn(
                        allies,
                        filteredAllies,
                        expandedAllyId,
                        allyClassFilter,
                        setAllyClassFilter,
                        toggleAlly,
                        () => setExpandedAllyId(null)
                    )}
                </div>

                {/* Enemies Column */}
                <div className="column-wrapper enemies-column">
                    <div className="column-top-bar enemies-bar">
                        <h3>Enemies ({enemies.length})</h3>
                        {expandedEnemyId && (
                            <button className="back-btn" onClick={() => setExpandedEnemyId(null)}>← Back to list</button>
                        )}
                    </div>
                    {renderColumn(
                        enemies,
                        filteredEnemies,
                        expandedEnemyId,
                        enemyClassFilter,
                        setEnemyClassFilter,
                        toggleEnemy,
                        () => setExpandedEnemyId(null)
                    )}
                </div>
            </div>
        </div>
    );
}

export default MatchupDashboard;