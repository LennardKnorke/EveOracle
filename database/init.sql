CREATE TABLE IF NOT EXISTS UserAccount (
    id BIGINT PRIMARY KEY,
    char_hash VARCHAR(255),
    char_name VARCHAR(255) NOT NULL UNIQUE,

    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMP,

    scopes TEXT,
    session_key VARCHAR(64) UNIQUE
);