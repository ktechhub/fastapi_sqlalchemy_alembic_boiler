from dotenv import load_dotenv

load_dotenv()

from app.services.redis_base import client as redis_client

# Delete all data from all Redis databases
redis_client.flushall()
