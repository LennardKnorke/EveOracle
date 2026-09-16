// frontend/src/components/EveOracleUI/ModelPredictionWidget.tsx

import React, { useState, useMemo } from 'react';
import { type TeamToken, isW2 } from '../../api/type';
import { type ModelManifest, type PredictionResult, predictMatchup } from '../../api/models';
import './ModelPredictionWidget.css';

function formatISK(value?: number): string {
    if (!value && value !== 0) return '0 ISK';
    const abs = Math.abs(value);
    const sign = value < 0 ? '-' : '+';
    if (abs >= 1e9) return `${sign}${(abs / 1e9).toFixed(2)}B ISK`;
    if (abs >= 1e6) return `${sign}${(abs / 1e6).toFixed(1)}M ISK`;
    if (abs >= 1e3) return `${sign}${(abs / 1e3).toFixed(0)}K ISK`;
    return `${sign}${abs.toLocaleString()} ISK`;
}

interface ModelPredictionWidgetProps {
    allies: TeamToken[];
    enemies: TeamToken[];
    availableModels: ModelManifest[];
    loadingModels: boolean;
}

export function ModelPredictionWidget({
    allies,
    enemies,
    availableModels,
    loadingModels,
}: ModelPredictionWidgetProps) {
    const [selectedModelName, setSelectedModelName] = useState<string>('');
    const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
    const [prediction, setPrediction] = useState<PredictionResult | null>(null);
    const [evalError, setEvalError] = useState<string | null>(null);

    // Auto-select first model if none chosen
    React.useEffect(() => {
        if (!selectedModelName && availableModels.length > 0) {
            setSelectedModelName(availableModels[0].model_name);
        }
    }, [availableModels, selectedModelName]);

    // Invalidate prediction when allies or enemies change
    React.useEffect(() => {
        setPrediction(null);
        setEvalError(null);
    }, [allies, enemies, selectedModelName]);

    const selectedModel = useMemo(() => {
        return availableModels.find((m) => m.model_name === selectedModelName);
    }, [availableModels, selectedModelName]);

    // Validation Logic: 1v1 requirement (Ally must be W2, Enemy can be W1, W2, or W3)
    const validation = useMemo(() => {
        if (!selectedModel) {
            return { isValid: false, message: 'Select a trained model.' };
        }

        if (allies.length === 0 && enemies.length === 0) {
            return { isValid: false, message: 'Assign 1 Ally and 1 Enemy in Team Manager.' };
        }

        if (allies.length !== 1 || enemies.length !== 1) {
            return {
                isValid: false,
                message: `1v1 Model requires exactly 1 Ally and 1 Enemy (Currently: ${allies.length} Allies vs ${enemies.length} Enemies).`,
            };
        }

        const allyToken = allies[0];
        if (!isW2(allyToken)) {
            return {
                isValid: false,
                message: 'Allied pilot must have both Pilot and Ship identified (W2 status).',
            };
        }

        return { isValid: true, message: null };
    }, [allies, enemies, selectedModel]);

    const handleEvaluate = async () => {
        if (!validation.isValid || !selectedModelName) return;

        setIsEvaluating(true);
        setEvalError(null);

        try {
            const result = await predictMatchup(selectedModelName, allies[0], enemies[0]);
            setPrediction(result);
        } catch (err: any) {
            setEvalError(err.message || 'Failed to query model prediction.');
        } finally {
            setIsEvaluating(false);
        }
    };

    const allyWinPct = prediction ? Math.round(prediction.p1_win_probability * 100) : 50;
    const enemyWinPct = 100 - allyWinPct;

    return (
        <div className="model-prediction-widget">
            <div className="widget-header">
                <div className="model-selection-group">
                    <label htmlFor="model-select">Tactical AI Model:</label>
                    <select
                        id="model-select"
                        className="model-dropdown"
                        value={selectedModelName}
                        onChange={(e) => setSelectedModelName(e.target.value)}
                        disabled={loadingModels || availableModels.length === 0}
                    >
                        {availableModels.map((m) => (
                            <option key={m.model_name} value={m.model_name}>
                                {m.model_name} ({m.architecture.type} • {m.metrics?.test_directional_accuracy ? `${Math.round(m.metrics.test_directional_accuracy * 100)}% Acc` : 'Trained'})
                            </option>
                        ))}
                        {availableModels.length === 0 && (
                            <option value="">{loadingModels ? 'Loading models...' : 'No models found'}</option>
                        )}
                    </select>
                </div>

                <div className="evaluate-action-group">
                    <button
                        type="button"
                        className={`btn-evaluate ${!validation.isValid ? 'btn-disabled' : ''}`}
                        onClick={handleEvaluate}
                        disabled={!validation.isValid || isEvaluating}
                        title={validation.message || 'Run encounter evaluation'}
                    >
                        {isEvaluating ? 'Evaluating...' : '⚡ Evaluate Matchup'}
                    </button>
                </div>
            </div>

            {/* Validation Notification Banner when encounter does not match model */}
            {!validation.isValid && validation.message && (
                <div className="validation-hint">
                    <span className="hint-icon">ℹ️</span> {validation.message}
                </div>
            )}

            {evalError && <div className="eval-error-banner">{evalError}</div>}

            {/* Prediction Telemetry Output */}
            {prediction && (
                <div className="prediction-results-panel">
                    <div className="prediction-summary-row">
                        <div className="verdict-group">
                            <span className="verdict-label">Matchup Forecast:</span>
                            <span
                                className={`verdict-badge ${
                                    prediction.predicted_winner === 'p1' ? 'verdict-win' : 'verdict-loss'
                                }`}
                            >
                                {prediction.predicted_winner === 'p1' ? '🎯 Favorable Engagement' : '⚠️ Unfavorable / High Risk'}
                            </span>
                        </div>

                        <div className="isk-trade-group">
                            <span className="isk-label">Expected Net ISK Trade:</span>
                            <span
                                className={`isk-value ${
                                    prediction.predicted_isk_trade >= 0 ? 'isk-positive' : 'isk-negative'
                                }`}
                            >
                                {formatISK(prediction.predicted_isk_trade)}
                            </span>
                        </div>
                    </div>

                    {/* Win Probability Bar */}
                    <div className="probability-container">
                        <div className="prob-labels">
                            <span className="ally-label">Allies: {allyWinPct}%</span>
                            <span className="enemy-label">Enemies: {enemyWinPct}%</span>
                        </div>
                        <div className="prob-bar-track">
                            <div
                                className="prob-bar-fill-ally"
                                style={{ width: `${allyWinPct}%` }}
                            />
                            <div
                                className="prob-bar-fill-enemy"
                                style={{ width: `${enemyWinPct}%` }}
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default ModelPredictionWidget;