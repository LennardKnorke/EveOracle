// frontend/src/components/TeamConstellation.tsx
import React, { useState } from 'react';

import {type CharIdentifier, type CharacterStats} from '../api/zkill.ts'

import './TeamManager.css';


export type ConstellationColumnKey = 'allies' | 'enemies' | 'neutrals';
export interface TeamConstellationProps {
    allies: CharacterStats[];
    enemies: CharacterStats[];
    neutrals: CharacterStats[];
    onMoveCharacter: (
        from: 'allies' | 'enemies' | 'neutrals',
        to: 'allies' | 'enemies' | 'neutrals',
        character: CharacterStats
    ) => void;
    onRemoveCharacter: (
        from: 'allies' | 'enemies' | 'neutrals',
        character: CharacterStats
    ) => void;
};


interface PlayerTeamTokenProps {
    character: CharacterStats;
    source: ConstellationColumnKey;
    onDragStart: (e: React.DragEvent<HTMLLIElement>, source: ConstellationColumnKey, character: CharacterStats) => void;
    onRemove: (source: ConstellationColumnKey, character: CharacterStats) => void;
};

export function PlayerTeamToken({ character, source, onDragStart, onRemove }: PlayerTeamTokenProps) {
    const portraitUrl = `https://images.evetech.net/characters/${character.char.char_id}/portrait?size=32`;
    const alliancePortraitUrl = `https://images.evetech.net/alliances/${character.char.alliance_id}/logo?size=32`;
    return (
        <li 
            className="PlayerTeamToken"
            draggable
            onDragStart={(e) => onDragStart(e, source, character)}
        >
            <div className="token">
                <img 
                    src={portraitUrl} 
                    alt={character.char.char_name} 
                    className="character-portrait"
                    loading="lazy"
                />
                <img 
                    src={alliancePortraitUrl} 
                    alt={character.char.char_name} 
                    className="alliance-portrait"
                    loading="lazy"
                />
                <span className="character-name">{character.char.char_name}</span>
            </div>
            
            <button 
                type="button" 
                onClick={(e) => {
                    e.stopPropagation(); // Prevents dragging from being triggered on click
                    onRemove(source, character);
                }}
            >
                Delete
            </button>
        </li>
    );
};

export function TeamManagerWindow({allies, enemies, neutrals, onMoveCharacter, onRemoveCharacter } : TeamConstellationProps){
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
        e.preventDefault(); // Required to allow a drop event
        e.dataTransfer.dropEffect = 'move';
    };

    const handleDragEnter = (e: React.DragEvent<HTMLDivElement>, key: ConstellationColumnKey) => {
        e.preventDefault();
        setDragOverColumn(key);
    };

    const handleDragLeave = () => {
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
                                    key={character.char.char_id}
                                    character={character}
                                    source={key}
                                    onDragStart={handleDragStart}
                                    onRemove={onRemoveCharacter}
                                />
                            ))
                        ) : (
                            <li className="empty">—</li>
                        )}
                    </ul>
                </div>
            ))}
        </div>
    );
}

export default TeamManagerWindow;