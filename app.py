import json
from pathlib import Path
import sys

import requests

GAME_URL = 'https://www.cheapshark.com/api/1.0/deals'
USER_AGENT = 'game-deal-tracker-project'
DATA_DIR = Path('data')
REQUEST_TIMEOUT = 30

def download_store_deals(game_store):
    try:
        response = requests.get(
            GAME_URL,
            headers={'User-Agent': USER_AGENT},
            params={'storeID': game_store, 'pageSize': 20},
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
    except requests.RequestException as e:
        sys.exit(f'Game data download failed: {e}')
    print(f'Deals status: {response.status_code}')
    return response.json()


def save_deals(content):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = DATA_DIR / 'sample_deals.json'

    with open(raw_path, 'w') as f:
        json.dump(content, f, indent=2)
    print(f'Saved to : {raw_path}')


def main():
    deals = download_store_deals(1)
    save_deals(deals)


if __name__ == '__main__':
    main()