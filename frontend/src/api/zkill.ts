
//frontend/src/api/zkill.ts
export interface CharIdentifier {
    char_name: string;
    char_id: string|number;
    corporation_id: string|number;
    alliance_id: string|number;
};
export interface CharacterStats {
    char: CharIdentifier;
    stats: any; // Here the zkilldict is saved
};

export function transformToCharacterStats(rawData: any): CharacterStats[] {
    if (!rawData) return [];
    const targetData = rawData.results !== undefined ? rawData.results : rawData;

    const mapSingleEntry = (entry: any): CharacterStats => {        
        const char: CharIdentifier = {
            char_name: entry.name || '',
            // Fallbacks handle camelCase or snake_case API conventions
            char_id: entry.char_id || 0,
            corporation_id: entry.corporationID || 0,
            alliance_id: entry.allianceID || 0,
        };

        return {
            char,
            stats: entry.stats || null
        };
    };

    // 2. If targetData is an Array, map over it directly
    if (Array.isArray(targetData)) {
        return targetData.map(mapSingleEntry);
    }

    // 3. If targetData is a Key/Value Dictionary object, iterate over its pairs
    if (typeof targetData === 'object' && targetData !== null) {
        return Object.entries(targetData).map(([_, value]: [string, any]) => {
            // Map the value object using our helper
            return mapSingleEntry(value);
        });
    }
    return [];
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