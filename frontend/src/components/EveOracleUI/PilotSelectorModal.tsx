// frontend/src/components/EveOracleUI/PilotSelectorModal.tsx

import React from 'react';
import { type TeamToken } from '../../api/type';
import './PilotSelectorModal.css';

interface PilotSelectorModalProps {
    isOpen: boolean;
    availablePilots: { token: TeamToken; column: string }[];
    onSelect: (pilotToken: TeamToken) => void;
    onClose: () => void;
}

export function PilotSelectorModal({ isOpen, availablePilots, onSelect, onClose }: PilotSelectorModalProps) {
    if (!isOpen) return null;

    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h4>Assign Pilot to Ship</h4>
                    <button className="modal-close-btn" onClick={onClose}>✕</button>
                </div>

                <div className="modal-body-note">
                    Select an unassigned pilot from your roster:
                </div>

                <ul className="modal-pilot-list">
                    {availablePilots.map(({ token, column }) => (
                        <li
                            key={token.id}
                            className="modal-pilot-item"
                            onClick={() => onSelect(token)}
                        >
                            <img
                                src={`https://images.evetech.net/characters/${token.character?.char_id}/portrait?size=32`}
                                alt={token.character?.char_name}
                                className="modal-pilot-portrait"
                            />
                            <div className="modal-pilot-details">
                                <span className="modal-pilot-name">{token.character?.char_name}</span>
                                <span className="modal-pilot-col">Column: {column.toUpperCase()}</span>
                            </div>
                        </li>
                    ))}
                    {availablePilots.length === 0 && (
                        <li className="modal-no-results">No unassigned pilots available.</li>
                    )}
                </ul>
            </div>
        </div>
    );
}

export default PilotSelectorModal;