from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "mysql+pymysql://root:passw0rd@localhost:3306/hsbc_autoassist"
    
    # JWT Settings
    SECRET_KEY: str = "hsbc-autoassist-secret-key-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # OpenAI GPT-4o
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = "gpt-4o"
    
    # Ollama Local LLM (Fallback)
    OLLAMA_API_URL: str = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    USE_OLLAMA_FALLBACK: bool = os.getenv("USE_OLLAMA_FALLBACK", "true").lower() == "true"
    
    # External APIs
    SPLUNK_API_URL: str = os.getenv("SPLUNK_API_URL", "")
    SPLUNK_API_TOKEN: str = os.getenv("SPLUNK_API_TOKEN", "")
    ANSIBLE_API_URL: str = os.getenv("ANSIBLE_API_URL", "")
    ANSIBLE_API_TOKEN: str = os.getenv("ANSIBLE_API_TOKEN", "")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://localhost:3000", 
        "https://localhost:3001",
        "http://77.37.45.138:3000",
        "http://77.37.45.138:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ]
    
    # HSBC Settings
    COMPANY_NAME: str = "HSBC"
    DEPARTMENT: str = "DC Automation Support Team"
    BOT_NAME: str = "DC AutoAssist"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()