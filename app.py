import json
import sys
from pathlib import Path

import requests

BASE_URL = 'https://www.cheapshark.com/api/1.0/'
USER_AGENT = 'game-deal-tracker-project'
DATA_DIR = Path('data')
DEALS_PAGE_SIZE = 20
REQUEST_TIMEOUT = 30
STEAM_STORE_ID = 1


def fetch_json(endpoint, params):
    try:
        response = requests.get(
            BASE_URL + endpoint,
            headers={'User-Agent': USER_AGENT},
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        sys.exit(f'Request to {endpoint} failed: {e}')
    print(f'{endpoint} status: {response.status_code}')
    return response.json()


def save_sample(content, file_name):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    file_path = DATA_DIR / file_name

    with open(file_path, 'w') as f:
        json.dump(content, f, indent=2)
    print(f'Saved to: {file_path}')


def main():
    deals = fetch_json('deals', {'storeID': STEAM_STORE_ID,
                                 'pageSize': DEALS_PAGE_SIZE})
    save_sample(deals, 'sample_deals.json')
    for deal in deals:
        print(f"Game name: {deal['title']} / Sale Price: {deal['salePrice']}")


if __name__ == '__main__':
    main()
