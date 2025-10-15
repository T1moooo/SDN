# Configuration module
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Switch connection settings
SWITCH_IP = os.getenv("SWITCH_IP", "192.168.1.1")
SWITCH_USERNAME = os.getenv("SWITCH_USERNAME", "admin")
SWITCH_PASSWORD = os.getenv("SWITCH_PASSWORD", "password")

# NX-API settings
NXAPI_URL = f"https://{SWITCH_IP}/ins"
NXAPI_HEADERS = {'Content-Type': 'application/json-rpc'}

# Flask settings
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
