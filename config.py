"""配置管理模块"""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

class Config:
    BASE_DIR = Path(__file__).parent.absolute()
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    
    SWITCH_IP = os.getenv("SWITCH_IP", "sbx-nxos-mgmt.cisco.com")
    SWITCH_PORT = int(os.getenv("SWITCH_PORT", 443))
    SWITCH_USERNAME = os.getenv("SWITCH_USERNAME", "admin")
    SWITCH_PASSWORD = os.getenv("SWITCH_PASSWORD", "Admin_1234!")
    SWITCH_VERIFY_SSL = os.getenv("SWITCH_VERIFY_SSL", "False").lower() == "true"
    SWITCH_TIMEOUT = int(os.getenv("SWITCH_TIMEOUT", 30))
    
    POLICIES_DIR = BASE_DIR / "policies"
    POLICIES_UPLOADED_DIR = POLICIES_DIR / "uploaded"
    POLICIES_EXAMPLES_DIR = POLICIES_DIR / "examples"
    
    LOGS_DIR = BASE_DIR / "logs"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    
    FRONTEND_DIR = BASE_DIR / "frontend"
    STATIC_DIR = FRONTEND_DIR / "static"
    TEMPLATES_DIR = FRONTEND_DIR / "templates"
    
    MAX_UPLOAD_SIZE = 1048576
    ALLOWED_EXTENSIONS = {"yaml", "yml"}
    DRY_RUN = os.getenv("DRY_RUN", "False").lower() == "true"
    
    @classmethod
    def init_directories(cls):
        for directory in [cls.POLICIES_DIR, cls.POLICIES_UPLOADED_DIR, cls.POLICIES_EXAMPLES_DIR, cls.LOGS_DIR, cls.LOGS_DIR / "operations", cls.FRONTEND_DIR, cls.STATIC_DIR, cls.STATIC_DIR / "css", cls.STATIC_DIR / "js"]:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate_config(cls):
        errors = []
        if cls.SWITCH_IP == "192.168.1.1":
            errors.append("SWITCH_IP not configured")
        return len(errors) == 0, errors
    
    @classmethod
    def get_switch_config(cls):
        return {"host": cls.SWITCH_IP, "port": cls.SWITCH_PORT, "username": cls.SWITCH_USERNAME, "password": cls.SWITCH_PASSWORD, "verify_ssl": cls.SWITCH_VERIFY_SSL, "timeout": cls.SWITCH_TIMEOUT}
    
    @classmethod
    def display_config(cls):
        return f"==================================================\nSDN QoS Policy Management - Configuration\n==================================================\nEnvironment: {cls.FLASK_ENV}\nFlask Host: {cls.FLASK_HOST}:{cls.FLASK_PORT}\nSwitch IP: {cls.SWITCH_IP}:{cls.SWITCH_PORT}\n==================================================\n"

config = Config()
