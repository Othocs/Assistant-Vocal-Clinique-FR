#!/usr/bin/env python3
"""
Test script for Supabase client database functionality
"""
import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client
from loguru import logger

# Load environment variables
load_dotenv(override=True)

async def test_supabase_connection():
    # Get Supabase credentials from environment variables
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        logger.error("Missing Supabase credentials in environment variables")
        return
    
    logger.info(f"Connecting to Supabase at {url}")
    
    try:
        # Create Supabase client
        client = create_client(url, key)
        
        # Test the connection by fetching data from the clients table
        response = client.table("clients").select("*").limit(5).execute()
        
        # Check if table exists by examining the response
        if "error" in response:
            logger.error(f"Error accessing clients table: {response['error']}")
            return
        
        logger.success(f"Successfully connected to Supabase and retrieved data")
        logger.info(f"Found {len(response.data)} clients in the database")
        
        # Test adding a test client
        test_client = {
            "first_name": "Test",
            "last_name": "User",
            "email": f"testuser{os.urandom(4).hex()}@example.com",  # Random email to avoid conflicts
            "phone": "+33123456789"
        }
        
        logger.info(f"Adding test client: {test_client['first_name']} {test_client['last_name']}")
        
        # Insert the test client
        insert_response = client.table("clients").insert(test_client).execute()
        
        if "error" in insert_response:
            logger.error(f"Error adding test client: {insert_response['error']}")
            return
        
        new_client = insert_response.data[0]
        logger.success(f"Successfully added test client with ID: {new_client['id']}")
        
        # Clean up by deleting the test client
        logger.info(f"Cleaning up: Deleting test client...")
        delete_response = client.table("clients").delete().eq("id", new_client['id']).execute()
        
        if "error" in delete_response:
            logger.error(f"Error deleting test client: {delete_response['error']}")
            return
        
        logger.success(f"Successfully deleted test client")
        logger.success("All Supabase tests passed successfully!")
        
    except Exception as e:
        logger.error(f"Error testing Supabase connection: {e}")

if __name__ == "__main__":
    # Run the async test function
    asyncio.run(test_supabase_connection()) 