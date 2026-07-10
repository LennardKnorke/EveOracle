
//frontend/src/api/zkill.ts


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