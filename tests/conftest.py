import os

# pytest runs this file before any test. Point the API at the test database
# before api.py is imported, so tests never touch the real data.
os.environ["DATABASE_URL"] = "postgresql:///game_deals_test"
