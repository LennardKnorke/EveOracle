import "./LocalChatCharacters.css";

interface LocalChatInputFieldProps {
    value: string;
    onChange: (value: string) => void;
}

export function LocalChatInputField({ value, onChange } : LocalChatInputFieldProps){
        return (
            <div className='input-area'>
                <p>Paste character names (one per line):</p>

                <textarea
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    rows={10}
                    cols={40}
                    placeholder="Enter characters here..."
                    className="character-textarea"
                />
            </div>
        );
};

export default LocalChatInputField;