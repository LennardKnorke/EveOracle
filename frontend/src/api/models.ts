// frontend/src/api/models.ts

import { apiClient } from './client';
import { type TeamToken } from './type';

export interface ModelManifest {
    model_name: string;
    version: string;
    created_at: string;
    training_date_range: [string, string];
    architecture: {
        type: string;
        input_dim: number;
    };
    input_schema: {
        feature_order: string[];
        log_transform_keys: string[];
        scaler: {
            means: Record<string, number>;
            stds: Record<string, number>;
        };
    };
    output_schema: {
        target_name: string;
        type: string;
        interpretation: string;
        inverse_transform_formula: string;
        win_threshold: number;
    };
    metrics: {
        val_huber_loss?: number;
        val_directional_accuracy?: number;
        test_huber_loss?: number;
        test_directional_accuracy?: number;
        [key: string]: any;
    };
}

export interface PredictionResult {
    model_name: string;
    predicted_log_isk: number;
    predicted_isk_trade: number;
    p1_win_probability: number;
    p2_win_probability: number;
    predicted_winner: 'p1' | 'p2';
}

export async function fetchAvailableModels(): Promise<ModelManifest[]> {
    try {
        return await apiClient<ModelManifest[]>('/model/available');
    } catch (err) {
        console.warn('Failed to fetch available models:', err);
        return [];
    }
}

export async function predictMatchup(
    modelName: string,
    p1: TeamToken,
    p2: TeamToken
): Promise<PredictionResult> {
    return await apiClient<PredictionResult>('/model/predict', {
        method: 'POST',
        body: JSON.stringify({
            model_name: modelName,
            p1,
            p2,
        }),
    });
}