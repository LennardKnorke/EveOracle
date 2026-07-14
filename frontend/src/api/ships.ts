// frontend/src/api/ships.ts

export interface ShipData {
    name: string;
    shipClass: string;
    faction: string;
}

let shipCache: Record<string, ShipData> | null = null;
let loadingPromise: Promise<Record<string, ShipData>> | null = null;

async function loadShips(): Promise<Record<string, ShipData>> {
    if (shipCache) return shipCache;
    if (loadingPromise) return loadingPromise;

    loadingPromise = (async () => {
        try {
            const response = await fetch('http://localhost:8080/static/ships.json');
            if (!response.ok) throw new Error('Failed to load ships.json');
            const data = await response.json();
            shipCache = data;
            return data;
        } finally {
            loadingPromise = null;
        }
    })();

    return loadingPromise;
}

export async function getShipName(shipTypeID: number): Promise<string> {
    const ships = await loadShips();
    const key = String(shipTypeID);
    return ships[key]?.name || `Ship ${shipTypeID}`;
}

export async function getShipData(shipTypeID: number): Promise<ShipData | null> {
    const ships = await loadShips();
    const key = String(shipTypeID);
    return ships[key] || null;
}