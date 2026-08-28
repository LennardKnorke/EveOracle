// frontend/src/components/TeamManager.tsx

import React, { useState } from 'react';
import { type TeamToken, type ColumnKey, isW1, isW2, isW3 } from '../../api/type';
import './TeamManager.css';


interface PlayerTeamTokenProps {
    token: TeamToken;
    source: ColumnKey;
    onDragStart: (e: React.DragEvent<HTMLLIElement>, source: ColumnKey, token: TeamToken) => void;
    onDropOnToken: (e: React.DragEvent<HTMLLIElement>, targetToken: TeamToken, targetColumn: ColumnKey) => void;
    onRemove: (source: ColumnKey, token: TeamToken) => void;
    onClickPilot: (token: TeamToken, source: ColumnKey) => void;
    onClickShip: (token: TeamToken, source: ColumnKey) => void;
    onDetachShip: (token: TeamToken, source: ColumnKey) => void;
}


export function PlayerTeamToken({
    token,
    source,
    onDragStart,
    onDropOnToken,
    onRemove,
    onClickPilot,
    onClickShip,
    onDetachShip,
}: PlayerTeamTokenProps) {
    const { character, ship } = token;

    const handleContextMenu = (e: React.MouseEvent) => {
        if (isW2(token)) {
            e.preventDefault();
            if (window.confirm(`Detach ${ship?.name} from ${character?.char_name}?`)) {
                onDetachShip(token, source);
            }
        }
    };

    const handleDragOver = (e: React.DragEvent<HTMLLIElement>) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const handleTokenDrop = (e: React.DragEvent<HTMLLIElement>) => {
        e.preventDefault();
        e.stopPropagation();
        onDropOnToken(e, token, source);
    };

    return (
        <li
            className={`player-team-token ${isW1(token) ? 'token-w1' : isW2(token) ? 'token-w2' : 'token-w3'}`}
            draggable
            onDragStart={(e) => onDragStart(e, source, token)}
            onDragOver={handleDragOver}
            onDrop={handleTokenDrop}
            onContextMenu={handleContextMenu}
            title={isW2(token) ? 'Right click to detach ship' : undefined}
        >
            <div className="token-info">
                {/* 2-Row Icon Cluster */}
                <div className="token-icons-grid">
                    {/* Top Row: Character Portrait + Ship Icon */}
                    <div className="icons-row top-row">
                        {character ? (
                            <img
                                src={`https://images.evetech.net/characters/${character.char_id}/portrait?size=64`}
                                alt={character.char_name}
                                className="character-portrait"
                                loading="lazy"
                            />
                        ) : (
                            <div
                                className="unassigned-pilot-placeholder"
                                onClick={() => onClickPilot(token, source)}
                                title="Click to assign a pilot"
                            >
                                👤+
                            </div>
                        )}

                        {ship ? (
                            <img
                                src={`https://images.evetech.net/types/${ship.id}/icon?size=32`}
                                alt={ship.name}
                                className="ship-icon"
                                onClick={() => onClickShip(token, source)}
                                title="Click to change ship (Right click to detach)"
                                onError={(e) => {
                                    (e.target as HTMLElement).style.display = 'none';
                                }}
                            />
                        ) : (
                            <div
                                className="unassigned-ship-placeholder"
                                onClick={() => onClickShip(token, source)}
                                title="Click to assign ship"
                            >
                                🚀+
                            </div>
                        )}
                    </div>

                    {/* Bottom Row: Corp Logo + Alliance Logo */}
                    {character && (character.corporation_id || character.alliance_id) ? (
                        <div className="icons-row bottom-row">
                            {character.corporation_id && (
                                <img
                                    src={`https://images.evetech.net/corporations/${character.corporation_id}/logo?size=32`}
                                    alt="Corporation"
                                    className="corp-logo"
                                    title={`Corp ID: ${character.corporation_id}`}
                                    loading="lazy"
                                />
                            )}
                            {character.alliance_id && (
                                <img
                                    src={`https://images.evetech.net/alliances/${character.alliance_id}/logo?size=32`}
                                    alt="Alliance"
                                    className="alliance-logo"
                                    title={`Alliance ID: ${character.alliance_id}`}
                                    loading="lazy"
                                />
                            )}
                        </div>
                    ) : (
                        /* Empty bottom spacer for W3 to maintain alignment */
                        <div className="icons-row bottom-row empty-bottom-row" />
                    )}
                </div>

                {/* Details Section */}
                <div className="pilot-details">
                    <div className="pilot-title-row">
                        {character ? (
                            <span className="character-name" onClick={() => !ship && onClickShip(token, source)}>
                                {character.char_name}
                            </span>
                        ) : (
                            <span
                                className="unassigned-pilot-label"
                                onClick={() => onClickPilot(token, source)}
                            >
                                Unknown Pilot
                            </span>
                        )}

                        {character?.standing !== null && character?.standing !== undefined && (
                            <span
                                className={`character-standing ${
                                    character.standing > 0
                                        ? 'standing-positive'
                                        : character.standing < 0
                                        ? 'standing-negative'
                                        : 'standing-neutral'
                                }`}
                            >
                                {character.standing > 0 ? `+${character.standing}` : character.standing}
                            </span>
                        )}
                    </div>

                    <div className="ship-title-row">
                        {ship ? (
                            <span className="ship-label" onClick={() => onClickShip(token, source)}>
                                {ship.name} {ship.shipClass ? `(${ship.shipClass})` : ''}
                            </span>
                        ) : (
                            <span className="no-ship-label" onClick={() => onClickShip(token, source)}>
                                + Assign Ship
                            </span>
                        )}
                    </div>
                </div>
            </div>

            <button
                type="button"
                className="token-remove-btn"
                title="Remove entry"
                onClick={(e) => {
                    e.stopPropagation();
                    onRemove(source, token);
                }}
            >
                ✕
            </button>
        </li>
    );
};

export interface TeamManagerProps {
    allies: TeamToken[];
    neutrals: TeamToken[];
    enemies: TeamToken[];
    onMoveToken: (from: ColumnKey, to: ColumnKey, token: TeamToken) => void;
    onMergeTokens: (draggedToken: TeamToken, fromCol: ColumnKey, targetToken: TeamToken, toCol: ColumnKey) => void;
    onRemoveToken: (from: ColumnKey, token: TeamToken) => void;
    onAddShipClick: (column: ColumnKey) => void;
    onClickPilotToken: (token: TeamToken, column: ColumnKey) => void;
    onClickShipToken: (token: TeamToken, column: ColumnKey) => void;
    onDetachShip: (token: TeamToken, column: ColumnKey) => void;
}


export function TeamManagerWindow({
    allies,
    neutrals,
    enemies,
    onMoveToken,
    onMergeTokens,
    onRemoveToken,
    onAddShipClick,
    onClickPilotToken,
    onClickShipToken,
    onDetachShip,
}: TeamManagerProps) {
    const [dragOverColumn, setDragOverColumn] = useState<ColumnKey | null>(null);

    const columns: { key: ColumnKey; label: string; items: TeamToken[]; themeClass: string }[] = [
        { key: 'allies', label: 'Allies', items: allies, themeClass: 'column-allies' },
        { key: 'neutrals', label: 'Neutrals', items: neutrals, themeClass: 'column-neutrals' },
        { key: 'enemies', label: 'Enemies', items: enemies, themeClass: 'column-enemies' },
    ];

    const handleDragStart = (
        e: React.DragEvent<HTMLLIElement>,
        source: ColumnKey,
        token: TeamToken
    ) => {
        e.dataTransfer.setData('application/json', JSON.stringify({ source, token }));
        e.dataTransfer.effectAllowed = 'move';
    };

    const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    };

    const handleDragEnter = (key: ColumnKey) => {
        setDragOverColumn(key);
    };

    const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
        const currentTarget = e.currentTarget;
        const relatedTarget = e.relatedTarget as Node | null;
        if (relatedTarget && currentTarget.contains(relatedTarget)) return;
        setDragOverColumn(null);
    };

    const handleDrop = (e: React.DragEvent<HTMLDivElement>, target: ColumnKey) => {
        e.preventDefault();
        setDragOverColumn(null);

        const rawData = e.dataTransfer.getData('application/json');
        if (!rawData) return;

        try {
            const { source, token } = JSON.parse(rawData) as { source: ColumnKey; token: TeamToken };
            if (source !== target) {
                onMoveToken(source, target, token);
            }
        } catch (error) {
            console.error('Failed to drop token:', error);
        }
    };

    const handleDropOnToken = (
        e: React.DragEvent<HTMLLIElement>,
        targetToken: TeamToken,
        targetColumn: ColumnKey
    ) => {
        const rawData = e.dataTransfer.getData('application/json');
        if (!rawData) return;

        try {
            const { source, token: draggedToken } = JSON.parse(rawData) as {
                source: ColumnKey;
                token: TeamToken;
            };

            // Merge if one is W1 and one is W3
            if (
                (isW1(draggedToken) && isW3(targetToken)) ||
                (isW3(draggedToken) && isW1(targetToken))
            ) {
                onMergeTokens(draggedToken, source, targetToken, targetColumn);
            } else if (source !== targetColumn) {
                onMoveToken(source, targetColumn, draggedToken);
            }
        } catch (error) {
            console.error('Failed to merge/drop token on token:', error);
        }
    };

    return (
        <div className="team-manager-window">
            {columns.map(({ key, label, items, themeClass }) => (
                <div
                    key={key}
                    className={`column ${themeClass} ${dragOverColumn === key ? 'drag-over' : ''}`}
                    onDragOver={handleDragOver}
                    onDragEnter={() => handleDragEnter(key)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, key)}
                >
                    <div className="column-header">
                        <h3>{label}</h3>
                        <div className="header-actions">
                            <span className="column-count">{items.length}</span>
                            <button
                                type="button"
                                className="add-ship-btn"
                                onClick={() => onAddShipClick(key)}
                                title="Add Spotted Ship (W3)"
                            >
                                + Ship
                            </button>
                        </div>
                    </div>

                    <ul
                        className="column-list"
                        onClick={(e) => {
                            if (e.target === e.currentTarget) {
                                onAddShipClick(key);
                            }
                        }}
                    >
                        {items.length > 0 ? (
                            items.map((token) => (
                                <PlayerTeamToken
                                    key={token.id}
                                    token={token}
                                    source={key}
                                    onDragStart={handleDragStart}
                                    onDropOnToken={handleDropOnToken}
                                    onRemove={onRemoveToken}
                                    onClickPilot={onClickPilotToken}
                                    onClickShip={onClickShipToken}
                                    onDetachShip={onDetachShip}
                                />
                            ))
                        ) : (
                            <li className="empty-state" onClick={() => onAddShipClick(key)}>
                                {dragOverColumn === key ? '⬇ Drop here' : 'Click to + Add Ship or drop pilots'}
                            </li>
                        )}
                    </ul>
                </div>
            ))}
        </div>
    );
}

export default TeamManagerWindow;