// frontend/src/api/type.ts

export interface CharIdentifier {
    char_name: string;
    id: string|number;
    corporation_id: string|number;
    alliance_id: string|number;
};

export interface CharacterStats {
    char: CharIdentifier;
    stats: any; // Here the zkilldict is saved
};

export interface ShipData {
    name: string;
    shipClass: string;
    faction: string;
};