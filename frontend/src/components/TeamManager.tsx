// frontend/src/components/TeamManager.tsx

import React, { useState } from 'react';
import { type CharacterStats } from '../api/zkill';
import './TeamManager.css';

export type ConstellationColumnKey = 'allies' | 'enemies' | 'neutrals';

export interface TeamConstellationProps {
    allies: CharacterStats[];
    enemies: CharacterStats[];
    neutrals: CharacterStats[];
    onMoveCharacter: (
        from: ConstellationColumnKey,
        to: ConstellationColumnKey,
        character: CharacterStats
    ) => void;
    onRemoveCharacter: (
        from: ConstellationColumnKey,
        character: CharacterStats
    ) => void;
}

interface PlayerTeamTokenProps {
    character: CharacterStats;
    source: ConstellationColumnKey;
    onDragStart: (e: React.DragEvent<HTMLLIElement>, source: ConstellationColumnKey, character: CharacterStats) => void;
    onRemove: (source: ConstellationColumnKey, character: CharacterStats) => void;
}

export function PlayerTeamToken({ character, source, onDragStart, onRemove }: PlayerTeamTokenProps) {
    const portraitUrl = `https://images.evetech.net/characters/${character.char.id}/portrait?size=32`;
    const alliancePortraitUrl = character.char.alliance_id
        ? `https://images.evetech.net/alliances/${character.char.alliance_id}/logo?size=32`
        : undefined;

    return (
        <li
            className="PlayerTeamToken"
            draggable
            onDragStart={(e) => onDragStart(e, source, character)}
        >
            <div className="token">
                <img src={portraitUrl} alt={character.char.char_name} className="character-portrait" loading="lazy" />
                {alliancePortraitUrl && (
                    <img src={alliancePortraitUrl} alt="Alliance" className="alliance-portrait" loading="lazy" />
                )}
                <span className="character-name">{character.char.char_name}</span>
            </div>
            <button
                type="button"
                onClick={(e) => {
                    e.stopPropagation();
                    onRemove(source, character);
                }}
            >
                ✕
            </button>
        </li>
    );
}

export function TeamManagerWindow({
    allies,
    enemies,
    neutrals,
    onMoveCharacter,
    onRemoveCharacter,
}: TeamConstellationProps) {
    const [dragOverColumn, setDragOverColumn] = useState<ConstellationColumnKey | null>(null);

    const columns: { key: ConstellationColumnKey; label: string; items: CharacterStats[] }[] = [
        { key: 'allies', label: 'Allies', items: allies },
        { key: 'enemies', label: 'Enemies', items: enemies },
        { key: 'neutrals', label: 'Neutrals', items: neutrals },
    ];

    const handleDragStart = (
        e: React.DragEvent<HTMLLIElement>,
        source: ConstellationColumnKey,
        character: CharacterStats
    ) => {
        e.dataTransfer.setData('text/plain', JSON.stringify({ source, character }));
        e.dataTransfer.effectAllowed = 'move';
    };

    const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault(); // Required to allow drop
        e.dataTransfer.dropEffect = 'move';
    };

    const handleDragEnter = (e: React.DragEvent<HTMLDivElement>, key: ConstellationColumnKey) => {
        e.preventDefault();
        setDragOverColumn(key);
    };

    const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
        // Only clear if we are truly leaving the container, not moving to a child
        const currentTarget = e.currentTarget;
        const relatedTarget = e.relatedTarget as Node | null;
        if (relatedTarget && currentTarget.contains(relatedTarget)) {
            // The cursor is still inside the container (on a child)
            return;
        }
        setDragOverColumn(null);
    };

    const handleDrop = (e: React.DragEvent<HTMLDivElement>, target: ConstellationColumnKey) => {
        e.preventDefault();
        setDragOverColumn(null);

        const rawData = e.dataTransfer.getData('text/plain');
        if (!rawData) return;

        try {
            const { source, character } = JSON.parse(rawData);
            if (source !== target) {
                onMoveCharacter(source as ConstellationColumnKey, target, character);
            }
        } catch (error) {
            console.error('Failed to drop character:', error);
        }
    };

    return (
        <div className="team-manager-window">
            {columns.map(({ key, label, items }) => (
                <div
                    key={key}
                    className={`column ${dragOverColumn === key ? 'drag-over' : ''}`}
                    onDragOver={handleDragOver}
                    onDragEnter={(e) => handleDragEnter(e, key)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, key)}
                >
                    <h3>{label} ({items.length})</h3>
                    <ul>
                        {items.length > 0 ? (
                            items.map((character) => (
                                <PlayerTeamToken
                                    key={character.char.id}
                                    character={character}
                                    source={key}
                                    onDragStart={handleDragStart}
                                    onRemove={onRemoveCharacter}
                                />
                            ))
                        ) : (
                            <li className="empty">
                                {dragOverColumn === key ? '⬇️ Drop here' : '—'}
                            </li>
                        )}
                    </ul>
                </div>
            ))}
        </div>
    );
}

export default TeamManagerWindow;