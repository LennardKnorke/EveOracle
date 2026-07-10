// frontend/src/api/auth.ts

export async function validate_session(session_key : string) : Promise<{ session_key: string | null, char_name: string | null }> {
    const response = await fetch(
        "http://localhost:8080/auth/validate_session/",
        {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${session_key}`,
                "Content-Type": "application/json"
            }
        }
    )
    if (!response.ok) {
        throw new Error("Something went wrong while validating session");
    }

    const data = await response.json();

    return {
        session_key: data.session_key ?? null,
        char_name: data.char_name ?? null
    };
};