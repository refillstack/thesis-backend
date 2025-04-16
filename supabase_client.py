from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL", "https://otkckrxodedjkipgnnqf.supabase.co")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Make sure to use service role key, not anon key

if not supabase_key:
    raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable is not set")

supabase = create_client(supabase_url, supabase_key) 