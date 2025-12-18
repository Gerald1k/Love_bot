import os
from pymongo import MongoClient

client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
db = client["bots"]
users_collection = db["users"]
gifts_collection = db["gifts"]

