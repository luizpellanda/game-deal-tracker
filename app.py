import json
from pathlib import Path

import requests

BASE_URL = "https://www.cheapshark.com/api/1.0/"
USER_AGENT = "game-deal-tracker-project"
DATA_DIR = Path("data")
DEALS_PAGE_SIZE = 20
REQUEST_TIMEOUT = 30
STEAM_STORE_ID = 1


class CheapSharkError(Exception):
    """CheapShark failed. status_code is its HTTP status (404, 429, ...) or None if it never answered."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def fetch_json(endpoint, params):
    try:
        response = requests.get(
            BASE_URL + endpoint,
            headers={"User-Agent": USER_AGENT},
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 429:
            wait_time = response.headers.get("Retry-After", "unknown")
            raise CheapSharkError(
                f"Rate limited on {endpoint} (429). Retry after {wait_time} seconds.",
                status_code=429,
            )
        response.raise_for_status()
    except requests.RequestException as e:
        # e.response exists when CheapShark answered with an error (like 404);
        # it is None when it never answered (timeout, no internet).
        status_code = e.response.status_code if e.response is not None else None
        raise CheapSharkError(
            f"Request to {endpoint} failed: {e}", status_code=status_code
        ) from e
    print(f"{endpoint} status: {response.status_code}")
    return response.json()


def save_sample(content, file_name):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    file_path = DATA_DIR / file_name

    with open(file_path, "w") as f:
        json.dump(content, f, indent=2)
    print(f"Saved to: {file_path}")


def main():
    deals = fetch_json(
        "deals", {"storeID": STEAM_STORE_ID, "pageSize": DEALS_PAGE_SIZE}
    )
    save_sample(deals, "sample_deals.json")
    for deal in deals:
        print(f"Game name: {deal['title']} / Sale Price: {deal['salePrice']}")


if __name__ == "__main__":
    main()
