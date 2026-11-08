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

CREATE INDEX IF NOT EXISTS prices_game_recorded_on ON price_history (game_id, recorded_on);
