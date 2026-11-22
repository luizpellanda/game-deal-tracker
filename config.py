"""Settings shared by every part of the API, read from the .env file."""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL is not set.")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    sys.exit("SECRET_KEY is not set.")
