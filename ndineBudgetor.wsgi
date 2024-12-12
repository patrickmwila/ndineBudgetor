import sys
import os

# Add application directory to Python path
sys.path.insert(0, '/var/www/html/ndineBudgetor')

# Set up environment variables
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Import the application
from app import app as application
