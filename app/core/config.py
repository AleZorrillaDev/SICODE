import os
import sys
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Configuración global de la aplicación.
    Utiliza Pydantic para validación y lectura de variables de entorno.
    """
    PROJECT_NAME: str = "Portal Corporativo CDAPP"
    PROJECT_VERSION: str = "1.0.0"
    
    # Configuración de Base de Datos
    DATABASE_URL: str = r"sqlite:///D:\SICODE\DB\dbSICODE.db"

    # Configuración de Correo (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "" # Configurar en .env
    SMTP_PASSWORD: str = "" # Configurar en .env (App Password)
    SMTP_FROM: str = "Portal SICODE <no-reply@sicode.com>"

    # --- Lógica de Rutas Dinámicas (Dev vs Exe) ---
    
    def get_app_root(self) -> str:
        """Retorna el directorio base persistente (donde está el .exe o el script)."""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.abspath(".")

    def get_static_dir(self) -> str:
        """Retorna la ruta de archivos estáticos (soporta PyInstaller _MEIPASS)."""
        if getattr(sys, 'frozen', False):
            # En modo .exe, los archivos estáticos están en la carpeta temporal
            base_path = sys._MEIPASS
            return os.path.join(base_path, "app", "static")
        else:
            # En modo normal, están en el directorio de trabajo actual
            return os.path.join(os.path.abspath("."), "app", "static")

    def get_template_path(self, relative_path: str) -> str:
        """
        Retorna la ruta absoluta correcta para una carpeta de templates.
        Ejemplo: relative_path = "app/modulos/inicio/templates"
        """
        root = self.get_app_root()
        
        # En modo .exe (frozen), root ya apunta a _MEIPASS o al ejecutable según implementacion get_app_root
        # Ajustamos para que apunte a _MEIPASS si es necesario
        if getattr(sys, 'frozen', False):
            root = sys._MEIPASS
        
        return os.path.join(root, relative_path)

    @property
    def STATIC_DIR(self) -> str:
        return self.get_static_dir()

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
