// frontend/src/api/ships.ts

import { type ShipInfo } from './type';
import { apiClient } from './client';

export interface CompleteShipData {
    ship_id: number;
    name: string;
    shipClass: string;
    faction: string;
    attributes: Record<string, any>;
    zkill_stats: Record<string, any>;
}

let shipsDatabaseCache: Record<string, CompleteShipData> | null = null;

/**
 * Loads all ships and global stats in a single bulk request from the backend.
 */
export async function prefetchAllShipStats(): Promise<Record<string, CompleteShipData>> {
    if (shipsDatabaseCache) return shipsDatabaseCache;

    try {
        // 1. Fetch static list of all ship IDs from ships.json
        const rawDogma = await apiClient<Record<string, any>>('/static/esi_static_data/ships.json');
        const shipIds = Object.keys(rawDogma).map(Number);

        // 2. Fetch dogma + global zKill stats in one batch call
        const batchData = await apiClient<Record<string, CompleteShipData>>('/ship/stats', {
            method: 'POST',
            body: JSON.stringify({ ship_ids: shipIds }),
        });

        shipsDatabaseCache = batchData;
        return batchData;
    } catch (err) {
        console.warn('Failed to prefetch ship stats batch, falling back to static dogma:', err);
        return {};
    }
}

export async function getShipsDatabase(): Promise<Record<string, ShipInfo>> {
    if (shipsDatabaseCache) {
        const simple: Record<string, ShipInfo> = {};
        for (const [id, data] of Object.entries(shipsDatabaseCache)) {
            simple[id] = {
                id: data.ship_id,
                name: data.name,
                shipClass: data.shipClass,
                faction: data.faction,
            };
        }
        return simple;
    }

    const full = await prefetchAllShipStats();
    const simple: Record<string, ShipInfo> = {};
    for (const [id, data] of Object.entries(full)) {
        simple[id] = {
            id: data.ship_id,
            name: data.name,
            shipClass: data.shipClass,
            faction: data.faction,
        };
    }
    return simple;
}

export async function searchShips(query: string): Promise<ShipInfo[]> {
    const db = await getShipsDatabase();
    const cleanQuery = query.toLowerCase().trim();
    if (!cleanQuery) return Object.values(db).slice(0, 30);

    return Object.values(db)
        .filter(
            (s) =>
                s.name.toLowerCase().includes(cleanQuery) ||
                (s.shipClass && s.shipClass.toLowerCase().includes(cleanQuery))
        )
        .slice(0, 50);
}