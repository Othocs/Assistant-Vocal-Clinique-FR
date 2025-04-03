#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""
Client Database Integration for Pipecat
Ce module fournit des fonctions pour interagir avec Supabase pour la gestion des clients
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from loguru import logger
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema

from functionCallingServices.supabase_client import supabase

# Helper function to format client data into a user-friendly string
def format_client_info(client: Dict) -> str:
    """Format client information into a readable string."""
    return (
        f"Client: {client['first_name']} {client['last_name']}\n"
        f"Email: {client['email']}\n"
        f"Phone: {client['phone']}"
    )

# Function call handlers for client operations
async def add_client(function_name: str, tool_call_id: str, args: Dict[str, Any], 
                    llm: Any, context: Any, result_callback: Callable) -> None:
    """
    Add a new client to the database
    
    Args:
        function_name: The name of the function being called
        tool_call_id: The ID of the tool call
        args: Arguments containing client information
        llm: The LLM service instance
        context: The context object
        result_callback: Callback to send results back to the LLM
    """
    try:
        # Extract client information from arguments
        first_name = args.get("first_name")
        last_name = args.get("last_name")
        email = args.get("email")
        phone = args.get("phone")
        
        # Validate inputs
        if not all([first_name, last_name, email, phone]):
            error_msg = {
                "success": False,
                "error": "Information client incomplète. Veuillez fournir prénom, nom, email et téléphone."
            }
            await llm.push_frame(TTSSpeakFrame("J'ai besoin de plus d'informations pour ajouter ce patient."))
            await result_callback(error_msg)
            return
        
        # Check if client already exists
        existing_client = await supabase.get_client_by_email(email)
        if existing_client:
            response = {
                "success": False,
                "error": f"Un patient avec l'email {email} existe déjà dans la base de données.",
                "client": existing_client
            }
            await result_callback(response)
            return
            
        # Add client to database
        await llm.push_frame(TTSSpeakFrame("Je vous ajoute à la base de données, veuillez patient un instant s'il vous plaît..."))
        client = await supabase.add_client(first_name, last_name, email, phone)
        
        success_response = {
            "success": True,
            "message": f"Patient {first_name} {last_name} ajouté avec succès.",
            "client": client
        }
        await result_callback(success_response)
    
    except Exception as e:
        logger.error(f"Error in add_client function: {e}")
        error_response = {
            "success": False,
            "error": f"Échec de l'ajout du client: {str(e)}"
        }
        await result_callback(error_response)

async def verify_client(function_name: str, tool_call_id: str, args: Dict[str, Any], 
                       llm: Any, context: Any, result_callback: Callable) -> None:
    """
    Verify if a client exists in the database
    
    Args:
        function_name: The name of the function being called
        tool_call_id: The ID of the tool call
        args: Arguments containing email or phone to verify
        llm: The LLM service instance
        context: The context object
        result_callback: Callback to send results back to the LLM
    """
    try:
        email = args.get("email")
        phone = args.get("phone")
        
        if not email and not phone:
            error_msg = {
                "exists": False,
                "error": "Veuillez fournir un email ou un numéro de téléphone pour vérifier le client."
            }
            await llm.push_frame(TTSSpeakFrame("J'ai besoin d'un email ou d'un numéro de téléphone pour vérifier si le client existe."))
            await result_callback(error_msg)
            return
        
        client = None
        if email:
            await llm.push_frame(TTSSpeakFrame(f"Je vérifie si un patient avec l'email {email} existe..."))
            client = await supabase.get_client_by_email(email)
        elif phone:
            await llm.push_frame(TTSSpeakFrame(f"Je vérifie si un patient avec le numéro {phone} existe..."))
            client = await supabase.get_client_by_phone(phone)
        
        if client:
            response = {
                "exists": True,
                "client": client,
                "message": f"Client trouvé: {client['first_name']} {client['last_name']}"
            }
            await result_callback(response)
        else:
            search_term = email if email else phone
            not_found_msg = {
                "exists": False,
                "message": f"Aucun client trouvé avec {email if email else 'le numéro ' + phone}."
            }
            await result_callback(not_found_msg)
    
    except Exception as e:
        logger.error(f"Error in verify_client function: {e}")
        error_response = {
            "exists": False,
            "error": f"Erreur lors de la vérification du client: {str(e)}"
        }
        await result_callback(error_response)

async def update_client(function_name: str, tool_call_id: str, args: Dict[str, Any], 
                      llm: Any, context: Any, result_callback: Callable) -> None:
    """
    Update a client's information in the database
    
    Args:
        function_name: The name of the function being called
        tool_call_id: The ID of the tool call
        args: Arguments containing client_id and updated information
        llm: The LLM service instance
        context: The context object
        result_callback: Callback to send results back to the LLM
    """
    try:
        # Extract information from arguments
        client_id = args.get("client_id")
        email = args.get("email")
        
        if not client_id and not email:
            error_msg = {
                "success": False,
                "error": "Veuillez fournir l'ID client ou l'email pour mettre à jour les informations."
            }
            await llm.push_frame(TTSSpeakFrame("J'ai besoin de l'identifiant ou de l'email du patient pour le mettre à jour."))
            await result_callback(error_msg)
            return
        
        # If email is provided but not client_id, find the client first
        if not client_id and email:
            client = await supabase.get_client_by_email(email)
            if client:
                client_id = client["id"]
            else:
                error_msg = {
                    "success": False,
                    "error": f"Aucun patient trouvé avec l'email {email}."
                }
                await result_callback(error_msg)
                return
        
        # Extract fields to update
        update_data = {}
        if args.get("first_name"):
            update_data["first_name"] = args.get("first_name")
        if args.get("last_name"):
            update_data["last_name"] = args.get("last_name")
        if args.get("new_email"):
            update_data["email"] = args.get("new_email")
        if args.get("phone"):
            update_data["phone"] = args.get("phone")
            
        if not update_data:
            error_msg = {
                "success": False,
                "error": "Aucune information fournie pour la mise à jour. Veuillez spécifier au moins un champ à mettre à jour."
            }
            await result_callback(error_msg)
            return
            
        # Update client in database
        await llm.push_frame(TTSSpeakFrame("Je mets à jour les informations du patient..."))
        updated_client = await supabase.update_client(client_id, update_data)
        
        success_response = {
            "success": True,
            "message": "Informations patient mises à jour avec succès.",
            "client": updated_client
        }
        await result_callback(success_response)
    
    except Exception as e:
        logger.error(f"Error in update_client function: {e}")
        error_response = {
            "success": False,
            "error": f"Échec de la mise à jour du patient: {str(e)}"
        }
        await result_callback(error_response)

async def find_client_by_email(function_name: str, tool_call_id: str, args: Dict[str, Any], 
                            llm: Any, context: Any, result_callback: Callable) -> None:
    """
    Find a client by their email address
    
    Args:
        function_name: The name of the function being called
        tool_call_id: The ID of the tool call
        args: Arguments containing email to search for
        llm: The LLM service instance
        context: The context object
        result_callback: Callback to send results back to the LLM
    """
    try:
        email = args.get("email")
        
        if not email:
            error_msg = {
                "found": False,
                "error": "Veuillez fournir une adresse email pour rechercher un patient."
            }
            await llm.push_frame(TTSSpeakFrame("J'ai besoin d'une adresse email pour trouver le patient."))
            await result_callback(error_msg)
            return
        
        await llm.push_frame(TTSSpeakFrame(f"Je recherche un patient avec l'email {email}..."))
        client = await supabase.get_client_by_email(email)
        
        if client:
            response = {
                "found": True,
                "client": client
            }
            await result_callback(response)
        else:
            not_found_msg = {
                "found": False,
                "message": f"Aucun patient trouvé avec l'email {email}."
            }
            await result_callback(not_found_msg)
    
    except Exception as e:
        logger.error(f"Error in find_client_by_email function: {e}")
        error_response = {
            "found": False,
            "error": f"Erreur lors de la recherche du patient: {str(e)}"
        }
        await result_callback(error_response)

async def find_client_by_phone(function_name: str, tool_call_id: str, args: Dict[str, Any], 
                            llm: Any, context: Any, result_callback: Callable) -> None:
    """
    Find a client by their phone number
    
    Args:
        function_name: The name of the function being called
        tool_call_id: The ID of the tool call
        args: Arguments containing phone to search for
        llm: The LLM service instance
        context: The context object
        result_callback: Callback to send results back to the LLM
    """
    try:
        phone = args.get("phone")
        
        if not phone:
            error_msg = {
                "found": False,
                "error": "Veuillez fournir un numéro de téléphone pour rechercher un patient."
            }
            await llm.push_frame(TTSSpeakFrame("J'ai besoin d'un numéro de téléphone pour trouver le patient."))
            await result_callback(error_msg)
            return
        
        await llm.push_frame(TTSSpeakFrame(f"Je recherche un patient avec le numéro {phone}..."))
        client = await supabase.get_client_by_phone(phone)
        
        if client:
            response = {
                "found": True,
                "client": client
            }
            await result_callback(response)
        else:
            not_found_msg = {
                "found": False,
                "message": f"Aucun client trouvé avec le numéro {phone}."
            }
            await result_callback(not_found_msg)
    
    except Exception as e:
        logger.error(f"Error in find_client_by_phone function: {e}")
        error_response = {
            "found": False,
            "error": f"Erreur lors de la recherche du client: {str(e)}"
        }
        await result_callback(error_response)

async def list_all_clients(function_name: str, tool_call_id: str, args: Dict[str, Any], 
                        llm: Any, context: Any, result_callback: Callable) -> None:
    """
    List all clients in the database
    
    Args:
        function_name: The name of the function being called
        tool_call_id: The ID of the tool call
        args: Empty argument dict
        llm: The LLM service instance
        context: The context object
        result_callback: Callback to send results back to the LLM
    """
    try:
        await llm.push_frame(TTSSpeakFrame("Je récupère tous les patients..."))
        clients = await supabase.get_clients()
        
        if not clients:
            await result_callback({
                "count": 0,
                "clients": [],
                "message": "Aucun patient trouvé dans la base de données."
            })
            return
        
        response = {
            "count": len(clients),
            "clients": clients,
            "message": f"Trouvé {len(clients)} patients dans la base de données."
        }
        
        await result_callback(response)
    
    except Exception as e:
        logger.error(f"Error in list_all_clients function: {e}")
        error_response = {
            "count": 0,
            "clients": [],
            "error": f"Erreur lors de la récupération des clients: {str(e)}"
        }
        await result_callback(error_response)

def get_client_function_schemas() -> List[FunctionSchema]:
    """
    Get the list of function schemas for client database operations
    
    Returns:
        List[FunctionSchema]: List of function schemas for client database operations
    """
    add_client_function = FunctionSchema(
        name="add_client",
        description="Ajouter un nouveau patient à la base de données",
        properties={
            "first_name": {
                "type": "string",
                "description": "Le prénom du patient",
            },
            "last_name": {
                "type": "string",
                "description": "Le nom de famille du patient",
            },
            "email": {
                "type": "string",
                "description": "L'adresse email du patient",
            },
            "phone": {
                "type": "string",
                "description": "Le numéro de téléphone du patient",
            },
        },
        required=["first_name", "last_name", "email", "phone"],
    )
    
    verify_client_function = FunctionSchema(
        name="verify_client",
        description="Vérifier si un client existe dans la base de données par email ou téléphone",
        properties={
            "email": {
                "type": "string",
                "description": "L'adresse email du patient à vérifier",
            },
            "phone": {
                "type": "string",
                "description": "Le numéro de téléphone du patient à vérifier",
            },
        },
        required=[],  # Requires either email or phone, but not both necessarily
    )
    
    update_client_function = FunctionSchema(
        name="update_client",
        description="Mettre à jour les informations d'un patient existant",
        properties={
            "client_id": {
                "type": "string",
                "description": "L'identifiant unique du patient à mettre à jour",
            },
            "email": {
                "type": "string",
                "description": "L'email actuel du patient (alternative à client_id pour identifier le client)",
            },
            "first_name": {
                "type": "string",
                "description": "Le nouveau prénom du patient",
            },
            "last_name": {
                "type": "string",
                "description": "Le nouveau nom de famille du patient",
            },
            "new_email": {
                "type": "string",
                "description": "La nouvelle adresse email du patient",
            },
            "phone": {
                "type": "string",
                "description": "Le nouveau numéro de téléphone du patient",
            },
        },
        required=[],  # Requires either client_id or email, plus at least one field to update
    )
    
    find_client_by_email_function = FunctionSchema(
        name="find_client_by_email",
        description="Rechercher un patient par adresse email",
        properties={
            "email": {
                "type": "string",
                "description": "L'adresse email à rechercher",
            },
        },
        required=["email"],
    )
    
    find_client_by_phone_function = FunctionSchema(
        name="find_client_by_phone",
        description="Rechercher un patient par numéro de téléphone",
        properties={
            "phone": {
                "type": "string",
                "description": "Le numéro de téléphone à rechercher",
            },
        },
        required=["phone"],
    )
    
    list_all_clients_function = FunctionSchema(
        name="list_all_clients",
        description="Lister tous les patients dans la base de données",
        properties={},
        required=[],
    )
    
    return [
        add_client_function,
        verify_client_function,
        update_client_function,
        find_client_by_email_function,
        find_client_by_phone_function,
        list_all_clients_function
    ]

def register_client_functions(llm_service: Any) -> None:
    """
    Register all client database functions with the LLM service
    
    Args:
        llm_service: The LLM service to register the functions with
    """
    llm_service.register_function("add_client", add_client)
    llm_service.register_function("verify_client", verify_client)
    llm_service.register_function("update_client", update_client)
    llm_service.register_function("find_client_by_email", find_client_by_email)
    llm_service.register_function("find_client_by_phone", find_client_by_phone)
    llm_service.register_function("list_all_clients", list_all_clients) 