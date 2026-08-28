// frontend/src/components/MatchupDashboard/FleetCompositionSummary.tsx

import React, { useMemo } from 'react';
import { type TeamToken, isW1 } from '../../api/type';
import './FleetCompositionSummary.css';

interface ShipClassCountItem {
    shipClass: string;
    count: number;
}

interface FleetCompositionSummaryProps {
    tokens: TeamToken[];
    selectedShipClass: string | null;
    onSelectShipClass: (shipClass: string | null) => void;
}

export function FleetCompositionSummary({
    tokens,
    selectedShipClass,
    onSelectShipClass,
}: FleetCompositionSummaryProps) {
    const { classCounts, unknownCount } = useMemo(() => {
        const countsMap = new Map<string, number>();
        let unknown = 0;

        tokens.forEach((t) => {
            if (t.ship && t.ship.shipClass) {
                const sClass = t.ship.shipClass.trim();
                countsMap.set(sClass, (countsMap.get(sClass) || 0) + 1);
            } else if (t.ship && !t.ship.shipClass) {
                const sClass = 'Unknown Class';
                countsMap.set(sClass, (countsMap.get(sClass) || 0) + 1);
            } else if (isW1(t)) {
                unknown += 1;
            }
        });

        const sortedClasses: ShipClassCountItem[] = Array.from(countsMap.entries())
            .map(([shipClass, count]) => ({ shipClass, count }))
            .sort((a, b) => b.count - a.count);

        return { classCounts: sortedClasses, unknownCount: unknown };
    }, [tokens]);

    if (tokens.length === 0) return null;

    const handleBadgeClick = (className: string) => {
        if (selectedShipClass === className) {
            onSelectShipClass(null); // Toggle off filter
        } else {
            onSelectShipClass(className);
        }
    };

    return (
        <div className="fleet-comp-summary">
            <div className="comp-badges-list">
                {/* Reset / All Badge */}
                {selectedShipClass !== null && (
                    <button
                        type="button"
                        className="comp-badge badge-all"
                        onClick={() => onSelectShipClass(null)}
                    >
                        Show All ({tokens.length})
                    </button>
                )}

                {/* Ship Class Badges */}
                {classCounts.map(({ shipClass, count }) => {
                    const isSelected = selectedShipClass === shipClass;
                    return (
                        <button
                            key={shipClass}
                            type="button"
                            className={`comp-badge ${isSelected ? 'badge-active' : ''}`}
                            onClick={() => handleBadgeClick(shipClass)}
                            title={`Filter by ${shipClass}`}
                        >
                            <span className="comp-badge-count">{count}x</span>
                            <span className="comp-badge-name">{shipClass}</span>
                        </button>
                    );
                })}

                {/* Unknown Ships Badge (W1) */}
                {unknownCount > 0 && (
                    <button
                        type="button"
                        className={`comp-badge badge-unknown ${
                            selectedShipClass === 'Unknown' ? 'badge-active' : ''
                        }`}
                        onClick={() => handleBadgeClick('Unknown')}
                        title="Filter pilots without an assigned ship"
                    >
                        <span className="comp-badge-count">{unknownCount}x</span>
                        <span className="comp-badge-name">Unknown</span>
                    </button>
                )}
            </div>
        </div>
    );
}

export default FleetCompositionSummary;