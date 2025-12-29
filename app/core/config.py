import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Configuración global de la aplicación.
    Utiliza Pydantic para validación y lectura de variables de entorno.
    """
    PROJECT_NAME: str = "Portal Corporativo CDAPP"
    PROJECT_VERSION: str = "1.0.0"
    
    # Configuración de Base de Datos
    # Se utiliza una ruta absoluta o relativa para SQLite
    DB_NAME: str = "portal.db"
    DATABASE_URL: str = f"sqlite:///./app/db/{DB_NAME}"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
