from pymongo import MongoClient
from backend.config import settings

# Global MongoDB Client
client = None
db = None

def get_db():
    global client, db
    if client is None:
        try:
            client = MongoClient(settings.mongodb_uri)
            db = client.gymsense
            # Test connection
            client.admin.command('ping')
            print("Successfully connected to MongoDB")
        except Exception as e:
            print(f"Failed to connect to MongoDB: {e}")
    return db

def get_users_collection():
    return get_db()["users"]

def get_sessions_collection():
    return get_db()["sessions"]
