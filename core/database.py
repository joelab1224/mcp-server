import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Singleton Database Manager for MongoDB connections"""
    
    _instance = None
    _client = None
    _database = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    async def connect(self):
        """Initialize MongoDB connection"""
        if self._client is None:
            mongodb_uri = os.getenv("MONGODB_URI")
            database_name = os.getenv("DATABASE_NAME")
            
            if not mongodb_uri or not database_name:
                raise ValueError("MONGODB_URI and DATABASE_NAME must be set in environment")
            
            self._client = AsyncIOMotorClient(mongodb_uri)
            self._database = self._client[database_name]
            
            # Test connection
            await self._client.admin.command('ping')
            logger.info(f"Connected to MongoDB database: {database_name}")
    
    async def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
            logger.info("MongoDB connection closed")
    
    def get_collection(self, collection_name: str):
        """Get a MongoDB collection"""
        if self._database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._database[collection_name]
    
    async def get_tenant_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get tenant configuration from assistants collection"""
        try:
            assistants = self.get_collection("assistants")
            config = await assistants.find_one({"tenant_id": int(tenant_id)})
            return config
        except Exception as e:
            logger.error(f"Error getting tenant config for {tenant_id}: {e}")
            return None
    
    async def get_tenant_tools(self, tenant_id: str) -> list:
        """Get enabled tools for a tenant"""
        config = await self.get_tenant_config(tenant_id)
        if config:
            return config.get("enabled_tools", [])
        return []
    
    async def get_tenant_api_keys(self, tenant_id: str) -> Dict[str, str]:
        """Get API keys for a tenant"""
        config = await self.get_tenant_config(tenant_id)
        if config:
            return config.get("api_keys", {})
        return {}
    
    async def create_tenant_config(self, tenant_id: str, config: Dict[str, Any]) -> bool:
        """Create or update tenant configuration"""
        try:
            assistants = self.get_collection("assistants")
            config["tenant_id"] = int(tenant_id)
            
            result = await assistants.replace_one(
                {"tenant_id": int(tenant_id)}, 
                config, 
                upsert=True
            )
            
            logger.info(f"Tenant config updated for {tenant_id}: {result.modified_count} modified, {result.upserted_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating tenant config for {tenant_id}: {e}")
            return False

# Global database instance
db = DatabaseManager()