
import os

class Config:
    
    SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ebokqkhwotfewvpsfemj.supabase.co")   
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVib2txa2h3b3RmZXd2cHNmZW1qIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTY0MjQxOCwiZXhwIjoyMDc3MjE4NDE4fQ.THk44izi0OPqEp6T5VMazLBVqd7J3NlKWRj44RUBGpA")   

   
    SECRET_KEY = os.getenv("SECRET_KEY", "supergeheimesleutel")  
