// frontend/src/api/type.ts
export type ColumnKey = 'allies' | 'neutrals' | 'enemies';

export interface CharacterStats {
    char_id: number | string;
    char_name: string;
    corporation_id?: number | string | null;
    alliance_id?: number | string | null;
    standing: number | null; // null = requesting user; > 0 = Ally; < 0 = Enemy; 0 = Neutral
    stats: Record<string, any>;
};

export interface ShipInfo {
    id: number | string;
    name: string;
    shipClass?: string;
    faction?: string;
};

export interface TeamToken {
    id: string; // Unique token ID
    character?: CharacterStats | null;
    ship?: ShipInfo | null;
};


export function isW1(token: TeamToken): boolean {
    return Boolean(token.character && !token.ship);
}
export function isW2(token: TeamToken): boolean {
    return Boolean(token.character && token.ship);
}
export function isW3(token: TeamToken): boolean {
    return Boolean(!token.character && token.ship);
}

export function getCategoryByStanding(
    standing: number | null | undefined,
    isFleet = false
): ColumnKey {
    if (isFleet) return 'allies';
    if (standing === null || standing === undefined || standing === 0) {
        return 'neutrals';
    }
    return standing > 0 ? 'allies' : 'enemies';
};