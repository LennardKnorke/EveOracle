// frontend/src/components/EveOracleUI/ShipSelectorModal.tsx

import React, { useState, useEffect, useRef } from 'react';
import { type ShipInfo } from '../../api/type';
import { searchShips } from '../../api/ships';
import './ShipSelectorModal.css';

interface ShipSelectorModalProps {
    isOpen: boolean;
    title?: string;
    onSelect: (ship: ShipInfo) => void;
    onClose: () => void;
}

export function ShipSelectorModal({ isOpen, title = 'Select Ship', onSelect, onClose }: ShipSelectorModalProps) {
    const [search, setSearch] = useState('');
    const [results, setResults] = useState<ShipInfo[]>([]);
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (isOpen) {
            setSearch('');
            searchShips('').then(setResults);
            setTimeout(() => inputRef.current?.focus(), 50);
        }
    }, [isOpen]);

    useEffect(() => {
        searchShips(search).then(setResults);
    }, [search]);

    if (!isOpen) return null;

    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h4>{title}</h4>
                    <button className="modal-close-btn" onClick={onClose}>✕</button>
                </div>

                <input
                    ref={inputRef}
                    type="text"
                    className="modal-search-input"
                    placeholder="Search by ship name or class..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />

                <ul className="modal-ship-list">
                    {results.map((ship) => (
                        <li key={ship.id} className="modal-ship-item" onClick={() => onSelect(ship)}>
                            <img
                                src={`https://images.evetech.net/types/${ship.id}/icon?size=32`}
                                alt={ship.name}
                                className="modal-ship-icon"
                                onError={(e) => {
                                    (e.target as HTMLElement).style.display = 'none';
                                }}
                            />
                            <div className="modal-ship-text">
                                <span className="modal-ship-name">{ship.name}</span>
                                <span className="modal-ship-class">{ship.shipClass || 'Unknown Class'}</span>
                            </div>
                        </li>
                    ))}
                    {results.length === 0 && <li className="modal-no-results">No matching ships found.</li>}
                </ul>
            </div>
        </div>
    );
}

export default ShipSelectorModal;