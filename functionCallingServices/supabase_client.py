#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os
from typing import Dict, List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv(override=True)

class SupabaseClient:
    """Client for interacting with Supabase database."""

    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            logger.error("Missing Supabase credentials in environment variables")
            raise ValueError("Supabase URL and key must be provided in environment variables")
        
        self.client = create_client(self.url, self.key)
        logger.info("Supabase client initialized")

    async def get_clients(self) -> List[Dict]:
        """Get all clients from the database."""
        try:
            response = self.client.table("clients").select("*").execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting clients: {e}")
            return []

    async def get_client_by_email(self, email: str) -> Optional[Dict]:
        """Get a client by email address."""
        try:
            response = self.client.table("clients").select("*").eq("email", email).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting client by email: {e}")
            return None

    async def get_client_by_phone(self, phone: str) -> Optional[Dict]:
        """Get a client by phone number."""
        try:
            response = self.client.table("clients").select("*").eq("phone", phone).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting client by phone: {e}")
            return None

    async def add_client(self, first_name: str, last_name: str, email: str, phone: str) -> Dict:
        """Add a new client to the database."""
        try:
            # Check if client with this email already exists
            existing = await self.get_client_by_email(email)
            if existing:
                logger.warning(f"Client with email {email} already exists")
                return existing
            
            client_data = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone
            }
            
            response = self.client.table("clients").insert(client_data).execute()
            return response.data[0]
        except Exception as e:
            logger.error(f"Error adding client: {e}")
            raise

    async def update_client(self, client_id: str, data: Dict) -> Dict:
        """Update a client's information."""
        try:
            response = self.client.table("clients").update(data).eq("id", client_id).execute()
            return response.data[0]
        except Exception as e:
            logger.error(f"Error updating client: {e}")
            raise

    async def delete_client(self, client_id: str) -> bool:
        """Delete a client from the database."""
        try:
            self.client.table("clients").delete().eq("id", client_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting client: {e}")
            return False

# Create a singleton instance
supabase = SupabaseClient() 