"""
config.py

Central place to load environment variables.
"""

from dotenv import load_dotenv
import os

# Load variables from .env file into environment
load_dotenv()

# Read OpenAI API key once
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DJANGO_ACCESS_TOKEN = os.getenv("DJANGO_ACCESS_TOKEN")
