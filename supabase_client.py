from supabase import create_client
import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file (works in local development)
load_dotenv()

# Get environment variables with better error handling
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Log information for debugging (not the actual key)
logger.info(f"Supabase URL: {supabase_url}")
logger.info(f"Supabase key available: {bool(supabase_key)}")

# Validate environment variables
if not supabase_url:
    logger.error("SUPABASE_URL environment variable is not set")
    supabase_url = "https://otkckrxodedjkipgnnqf.supabase.co"  # Fallback value
    logger.info(f"Using fallback SUPABASE_URL: {supabase_url}")

if not supabase_key:
    logger.error("SUPABASE_SERVICE_ROLE_KEY environment variable is not set")
    raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable is not set. This is required to connect to Supabase.")

try:
    # Create the client with proper error handling
    supabase = create_client(supabase_url, supabase_key)
    logger.info("Supabase client created successfully")
except Exception as e:
    logger.error(f"Error creating Supabase client: {str(e)}")
    raise 