import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    HUGGINGFACEHUB_API_TOKEN: str = ""
    GROQ_API_KEY: str = ""  # Load from .env file
    POSTGRES_URL: str = "postgresql+psycopg2://postgres:password@localhost:5432/urbanistica"
    
    # Resolves to AttiRegistro/Urbanistica/normativa-urbanistica-italia/database/normativa.db
    SQLITE_DB_PATH: str = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 
        "../../../../../AttiRegistro/Urbanistica/normativa-urbanistica-italia/database/normativa.db"
    ))
    
    class Config:
        env_file = ".env"

settings = Settings()
