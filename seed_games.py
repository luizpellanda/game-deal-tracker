from app import fetch_json

GAME_IDS = [
    126,     # Sid Meier's Civilization IV
    163295,  # Quern - Undying Thoughts
    117,     # Company of Heroes
    88304,   # Borderlands 2
    204144,  # Overpass
    279127,  # Cross Blitz
    158317,  # Owlboy
    166740,  # For The King
    279822,  # War Hospital
    218578,  # Werewolf: the Apocalypse - Heart of the Forest
    290092,  # SteamWorld Heist II
    199102,  # Warhammer: Chaosbane
    208,     # Company of Heroes: Opposing Fronts
    173596,  # Frostpunk
    204666,  # WRC 8 FIA World Rally Championship
    136930,  # This War of Mine
    429,     # Hitman: Blood Money
    278103,  # Nickelodeon All-Star Brawl 2
    150371,  # We Are The Dwarves
    145148,  # Dropsy
]


def main():
    ids_text = ','.join(str(game_id) for game_id in GAME_IDS)
    games = fetch_json('games', {'ids': ids_text})
    print(f'Games received: {len(games)}')


if __name__ == '__main__':
    main()
