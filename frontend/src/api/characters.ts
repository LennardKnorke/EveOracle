//src/api/characters.ts
import { apiClient } from "./client"


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


export async function fetch_fleet_stats(): Promise<CharacterStats[]> {
    return apiClient<CharacterStats[]>('/fleet/status');
};


export async function fetch_zkill_char_stats(session_key : string, characters : string[]) {
    const response = await fetch(
        "http://localhost:8080/stats/char",
        {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${session_key}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ characters })  
        }
    )
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Request failed with status ${response.status}`);
    }
    return response.json();
};

