import React from 'react';

import "./LocalChatCharacters.css";


interface LocalChatInputFieldProps {
    value: string;
    onChange: (value: string) => void;
    disabled?: boolean;
}

export function LocalChatInputField({ value, onChange, disabled }: LocalChatInputFieldProps) {
    return (
        <div>
            <label htmlFor="local-chat-input">Paste character names (one per line):</label>
            <textarea
                id="local-chat-input"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                rows={8}
                cols={35}
                placeholder="Paste pilot names here..."
                disabled={disabled}
                /* Disable browser extensions & spellchecks on pilot names */
                spellCheck={false}
                autoCorrect="off"
                autoCapitalize="off"
                data-gramm="false"
                data-gramm_editor="false"
                data-enable-grammarly="false"
            />
        </div>
    );
}

export default LocalChatInputField;