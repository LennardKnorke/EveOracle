// frontend/src/api/ships.ts

import { type ShipInfo } from './type';
import { apiClient } from './client';

let shipsCache: Record<string, ShipInfo> | null = null;

export async function getShipsDatabase(): Promise<Record<string, ShipInfo>> {
    if (shipsCache) return shipsCache;

    try {
        const rawData = await apiClient<Record<string, any>>('/static/esi_static_data/ships.json');
        const parsed: Record<string, ShipInfo> = {};

        for (const [key, val] of Object.entries(rawData)) {
            parsed[key] = {
                id: key,
                name: val.name,
                shipClass: val.shipClass,
                faction: val.faction,
            };
        }

        shipsCache = parsed;
        return parsed;
    } catch (err) {
        console.warn('Failed to load ships.json from static backend mount:', err);
        return {};
    }
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