import sys
import os

# Defina o caminho do projeto
project_home = '/home/Wellton/site_cef07'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Importe a aplicação Flask
from app import app as application  # Certifique-se de que 'app' corresponde ao nome do seu arquivo principal sem a extensão .py
