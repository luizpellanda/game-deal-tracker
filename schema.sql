CREATE TABLE IF NOT EXISTS games (
    id integer,
    title text NOT NULL,
    steam_app_id text,
    thumb_url text,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS price_history (
    game_id integer NOT NULL,
    store_id integer NOT NULL,
    sale_price NUMERIC(10, 2) NOT NULL,
    normal_price NUMERIC(10, 2) NOT NULL,
    recorded_on DATE NOT NULL,
    CONSTRAINT fk_price_history
        FOREIGN KEY (game_id)
        REFERENCES games (id),
    UNIQUE(game_id, store_id, recorded_on)
);

CREATE TABLE IF NOT EXISTS users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username text NOT NULL,
    password_hash text NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_valid_username
        CHECK (username ~ '^[a-z0-9_]{3,20}$'),
    UNIQUE(username)
);

CREATE TABLE IF NOT EXISTS watchlist (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL,
    game_id INTEGER NOT NULL,
    target_price NUMERIC(10,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_valid_target_price
        CHECK (target_price > 0 AND target_price <= 1000),
    CONSTRAINT fk_watchlist_user
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_watchlist_game
        FOREIGN KEY (game_id) REFERENCES games (id),
    CONSTRAINT uq_user_game
        UNIQUE (user_id, game_id)
);

CREATE INDEX IF NOT EXISTS prices_game_recorded_on ON price_history (game_id, recorded_on);
