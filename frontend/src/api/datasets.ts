


export interface DataSet_Summary {
    name : string;
    num_datapoints: number;
    created_at:Date;
    last_updated:Date;
};



export async function fetch_datasets_infos(session_key : string) {
    const response = await fetch(
        "http://localhost:8080/dataset/datasets_sum",
        {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${session_key}`,
                "Content-Type": "application/json"
            }
        }
    )

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Request failed with status ${response.status}`);
    }

    return response.json();
}
