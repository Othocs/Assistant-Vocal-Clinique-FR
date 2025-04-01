"""
Google Calendar integration for Pipecat - Version française
Ce module fournit des fonctions pour interagir avec l'API Google Calendar pour la planification des patients
"""

import os
import datetime
from typing import Dict, List, Any, Optional
import asyncio
from dateutil import parser
import pytz
import locale

# Set French locale for date formatting
try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'fr_FR')
    except:
        pass  # Fallback to system locale if French is not available

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.frames.frames import TTSSpeakFrame

# If modifying these scopes, delete the token.pickle file
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Set Paris timezone as default
TIMEZONE = 'Europe/Paris'
TIMEZONE_PYTZ = pytz.timezone(TIMEZONE)

def get_calendar_service():
    """
    Get an authorized Google Calendar service
    Returns a Calendar service object with appropriate credentials
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    # If there are no valid credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service

def get_current_time():
    """
    Get the current time in Paris timezone
    
    Returns:
        datetime: Current datetime in Paris timezone
    """
    return datetime.datetime.now(TIMEZONE_PYTZ)

def parse_relative_date(date_str: str) -> datetime.date:
    """
    Parse a relative date reference in French like 'aujourd'hui', 'demain', 'lundi', etc.
    
    Args:
        date_str: String representing a date, either absolute or relative (in French)
        
    Returns:
        date: The parsed date object
    """
    date_str = date_str.lower()
    now = get_current_time()
    today = now.date()
    
    # Handle common relative date references in French
    if date_str in ['aujourd\'hui', "aujourd'hui", 'ce jour']:
        return today
    elif date_str in ['demain']:
        return today + datetime.timedelta(days=1)
    elif date_str in ['après-demain', 'apres-demain', 'après demain', 'apres demain']:
        return today + datetime.timedelta(days=2)
    elif date_str in ['semaine prochaine', 'la semaine prochaine', 'dans une semaine']:
        return today + datetime.timedelta(days=7)
    
    # Handle day of week references in French
    days_of_week = {
        'lundi': 0, 'mardi': 1, 'mercredi': 2, 'jeudi': 3,
        'vendredi': 4, 'samedi': 5, 'dimanche': 6
    }
    
    for day, offset in days_of_week.items():
        if day in date_str:
            # Get the number of days until the next occurrence of that day
            days_ahead = offset - today.weekday()
            if days_ahead <= 0 or 'prochain' in date_str:  # If today's the day or already passed, use next week
                days_ahead += 7
            return today + datetime.timedelta(days=days_ahead)
    
    # Try to parse as a normal date
    try:
        return parser.parse(date_str, dayfirst=True).date()  # Use dayfirst=True for European format (DD/MM/YYYY)
    except Exception:
        # If we can't parse it, default to today
        return today

async def get_current_date(function_name: str, tool_call_id: str, args: Dict, llm: Any, context: Any, result_callback: Any) -> None:
    """
    Get the current date and time in Paris timezone
    
    Args:
        function_name: The name of the function being called
        tool_call_id: The ID of the tool call
        args: Empty args dict
        llm: The LLM service instance
        context: The context object
        result_callback: Callback to send results back to the LLM
    """
    try:
        now = get_current_time()
        
        # Format date in French style
        weekday = now.strftime("%A").capitalize()
        day = now.strftime("%d")
        month = now.strftime("%B").capitalize()
        year = now.strftime("%Y")
        time = now.strftime("%H:%M")
        
        # Format: "Lundi 20 Janvier 2023"
        formatted_date = f"{weekday} {day} {month} {year}"
        
        await result_callback({
            "current_date": now.strftime("%d/%m/%Y"),  # DD/MM/YYYY format
            "formatted_date": formatted_date,
            "current_day": weekday,
            "current_time": time,
            "timezone": TIMEZONE,
            "is_weekday": now.weekday() < 5
        })
        
    except Exception as e:
        await result_callback({"error": str(e)})

async def check_availability(function_name: str, tool_call_id: str, args: Dict, llm: Any, context: Any, result_callback: Any) -> None:
    """
    Check doctor's availability for a given date
    
    Args:
        function_name: The name of the function being called
        tool_call_id: The ID of the tool call
        args: Arguments containing date to check availability
        llm: The LLM service instance
        context: The context object
        result_callback: Callback to send results back to the LLM
    """
    try:
        # Parse the date from arguments
        date_str = args.get('date')
        if not date_str:
            await result_callback({"available_slots": [], "error": "Aucune date fournie"})
            return

        # Parse date, handling relative references
        date = parse_relative_date(date_str)
        
        # If the parsed date is a weekend, inform the user
        if date.weekday() >= 5:  # Saturday or Sunday
            await llm.push_frame(TTSSpeakFrame(
                f"Je suis désolé, mais notre clinique est fermée le week-end. "
                f"La date que vous avez mentionnée, {date.strftime('%A %d %B').capitalize()}, tombe un week-end. "
                "Souhaitez-vous vérifier la disponibilité pour le lundi suivant à la place ?"
            ))
            
            # Get the next Monday
            while date.weekday() >= 5:
                date += datetime.timedelta(days=1)
                
            date_str = date.strftime("%d/%m/%Y")  # Format as DD/MM/YYYY
            
        # Get calendar service
        service = get_calendar_service()
        
        # Get the doctor's calendar ID (using primary calendar for now)
        calendar_id = 'primary'
        
        # Set time boundaries for the specified date
        time_min = datetime.datetime.combine(date, datetime.time.min).replace(tzinfo=TIMEZONE_PYTZ).isoformat()
        time_max = datetime.datetime.combine(date, datetime.time.max).replace(tzinfo=TIMEZONE_PYTZ).isoformat()
        
        # Get events from the calendar
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Define working hours (9 AM to 5 PM)
        working_hours_start = 9  # 9h
        working_hours_end = 17   # 17h
        slot_duration = 30       # 30 minutes per slot
        
        # Generate all possible slots
        all_slots = []
        for hour in range(working_hours_start, working_hours_end):
            for minute in [0, 30]:
                slot_time = f"{hour:02d}h{minute:02d}" if minute > 0 else f"{hour:02d}h"
                all_slots.append(slot_time)
        
        # Mark booked slots
        booked_slots = []
        for event in events:
            start = event['start'].get('dateTime')
            if start:
                start_time = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                # Convert to Paris time
                start_time = start_time.astimezone(TIMEZONE_PYTZ)
                slot = f"{start_time.hour:02d}h{start_time.minute:02d}" if start_time.minute > 0 else f"{start_time.hour:02d}h"
                booked_slots.append(slot)
        
        # Find available slots
        available_slots = [slot for slot in all_slots if slot not in booked_slots]
        
        # Format the date nicely for display in French
        formatted_date = date.strftime("%A %d %B %Y").capitalize()
        
        await result_callback({
            "date": date_str,
            "formatted_date": formatted_date,
            "available_slots": available_slots,
            "is_today": date == get_current_time().date(),
            "is_weekday": date.weekday() < 5
        })
        
    except Exception as e:
        await result_callback({"error": str(e)})

async def schedule_appointment(function_name: str, tool_call_id: str, args: Dict, llm: Any, context: Any, result_callback: Any) -> None:
    """
    Schedule a new appointment for a patient
    
    Args:
        function_name: The name of the function being called
        tool_call_id: The ID of the tool call
        args: Arguments containing appointment details
        llm: The LLM service instance
        context: The context object
        result_callback: Callback to send results back to the LLM
    """
    try:
        # Extract appointment details from arguments
        patient_name = args.get('patient_name')
        date_str = args.get('date')
        time_str = args.get('time')
        reason = args.get('reason', 'Consultation médicale')
        calendar_id = args.get('calendar_id', 'primary')  # Utilise 'primary' par défaut, mais permet de spécifier un autre calendrier
        
        if not all([patient_name, date_str, time_str]):
            await result_callback({
                "success": False,
                "error": "Informations manquantes pour le rendez-vous"
            })
            return
        
        # Parse date and time, handling relative references
        date = parse_relative_date(date_str)
        
        # Parse time in French format (e.g., "14h30" or "14h")
        if 'h' in time_str:
            parts = time_str.split('h')
            hour = int(parts[0])
            minute = int(parts[1]) if parts[1] else 0
        else:
            # Try to parse as HH:MM format as fallback
            parts = time_str.split(':')
            if len(parts) == 2:
                hour = int(parts[0])
                minute = int(parts[1])
            else:
                # Just hour
                hour = int(time_str)
                minute = 0
        
        # Check if the date is a weekend
        if date.weekday() >= 5:  # Saturday or Sunday
            await result_callback({
                "success": False,
                "error": f"Impossible de prendre rendez-vous le week-end. La date {date.strftime('%A %d %B').capitalize()} tombe un week-end."
            })
            return
            
        # Check if the time is within working hours
        if hour < 9 or hour >= 17 or (hour == 17 and minute > 0):
            await result_callback({
                "success": False,
                "error": "Impossible de prendre rendez-vous en dehors des heures d'ouverture (9h à 17h)."
            })
            return
            
        # Create start and end times (appointments are 30 minutes by default)
        start_time = datetime.datetime.combine(date, datetime.time(hour, minute))
        # Apply the Paris timezone
        start_time = TIMEZONE_PYTZ.localize(start_time)
        end_time = start_time + datetime.timedelta(minutes=30)
        
        # Format times for Google Calendar API
        start_time_str = start_time.isoformat()
        end_time_str = end_time.isoformat()
        
        # Get calendar service
        service = get_calendar_service()
        
        # Create event
        event = {
            'summary': f"Rendez-vous: {patient_name}",
            'description': reason,
            'start': {
                'dateTime': start_time_str,
                'timeZone': TIMEZONE,
            },
            'end': {
                'dateTime': end_time_str,
                'timeZone': TIMEZONE,
            },
        }
        
        # Add the event to the calendar
        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        
        # Format the date and time nicely for the result in French
        formatted_date = date.strftime("%A %d %B %Y").capitalize()
        formatted_time = f"{hour:02d}h{minute:02d}" if minute > 0 else f"{hour:02d}h"
        
        # Obtenir le nom du calendrier utilisé
        calendar_name = "Principal"
        if calendar_id != 'primary':
            try:
                calendar_info = service.calendars().get(calendarId=calendar_id).execute()
                calendar_name = calendar_info.get('summary', 'Spécialiste')
            except:
                pass
        
        await result_callback({
            "success": True,
            "appointment_id": event['id'],
            "patient_name": patient_name,
            "date": date_str,
            "formatted_date": formatted_date,
            "time": formatted_time,
            "reason": reason,
            "calendar_id": calendar_id,
            "calendar_name": calendar_name,
            "message": f"Rendez-vous programmé pour {patient_name} le {formatted_date} à {formatted_time} avec {calendar_name}"
        })
        
    except Exception as e:
        await result_callback({
            "success": False,
            "error": str(e)
        })

async def cancel_appointment(function_name: str, tool_call_id: str, args: Dict, llm: Any, context: Any, result_callback: Any) -> None:
    """
    Cancel an existing appointment
    
    Args:
        function_name: The name of the function being called
        tool_call_id: The ID of the tool call
        args: Arguments containing appointment identification details
        llm: The LLM service instance
        context: The context object
        result_callback: Callback to send results back to the LLM
    """
    try:
        # Extract appointment details
        appointment_id = args.get('appointment_id')
        patient_name = args.get('patient_name')
        date_str = args.get('date')
        
        if not appointment_id and not (patient_name and date_str):
            await result_callback({
                "success": False,
                "error": "Informations manquantes. Veuillez fournir soit l'identifiant du rendez-vous, soit le nom du patient et la date"
            })
            return
        
        # Get calendar service
        service = get_calendar_service()
        
        if appointment_id:
            # Direct deletion by ID
            service.events().delete(calendarId='primary', eventId=appointment_id).execute()
            await result_callback({
                "success": True,
                "message": f"Le rendez-vous avec l'identifiant {appointment_id} a été annulé"
            })
        else:
            # Parse date, handling relative references
            date = parse_relative_date(date_str)
            
            # Find appointment by patient name and date
            time_min = datetime.datetime.combine(date, datetime.time.min).replace(tzinfo=TIMEZONE_PYTZ).isoformat()
            time_max = datetime.datetime.combine(date, datetime.time.max).replace(tzinfo=TIMEZONE_PYTZ).isoformat()
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            found = False
            
            for event in events:
                if patient_name in event.get('summary', ''):
                    service.events().delete(calendarId='primary', eventId=event['id']).execute()
                    found = True
                    break
            
            if found:
                # Format the date nicely for the result in French
                formatted_date = date.strftime("%A %d %B %Y").capitalize()
                
                await result_callback({
                    "success": True,
                    "message": f"Le rendez-vous pour {patient_name} le {formatted_date} a été annulé"
                })
            else:
                await result_callback({
                    "success": False,
                    "error": f"Aucun rendez-vous trouvé pour {patient_name} le {date_str}"
                })
    
    except Exception as e:
        await result_callback({
            "success": False,
            "error": str(e)
        })

async def list_calendars(function_name: str, tool_call_id: str, args: Dict, llm: Any, context: Any, result_callback: Any) -> None:
    """
    Liste tous les calendriers et sous-calendriers disponibles pour l'utilisateur
    
    Args:
        function_name: The name of the function being called
        tool_call_id: The ID of the tool call
        args: Empty args dict
        llm: The LLM service instance
        context: The context object
        result_callback: Callback to send results back to the LLM
    """
    try:
        # Get calendar service
        service = get_calendar_service()
        
        # Récupère la liste des calendriers
        calendar_list = service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        
        # Prépare le résultat sous forme de liste structurée
        calendar_info = []
        primary_calendar_id = None
        
        for calendar in calendars:
            # Obtient l'ID du calendrier principal
            if calendar.get('primary', False):
                primary_calendar_id = calendar['id']
                
            calendar_info.append({
                "id": calendar['id'],
                "summary": calendar.get('summary', 'Sans titre'),
                "description": calendar.get('description', ''),
                "is_primary": calendar.get('primary', False),
                "access_role": calendar.get('accessRole', ''),
                "background_color": calendar.get('backgroundColor', ''),
                "time_zone": calendar.get('timeZone', '')
            })
        
        await result_callback({
            "calendars": calendar_info,
            "primary_calendar_id": primary_calendar_id,
            "total_calendars": len(calendar_info)
        })
    
    except Exception as e:
        await result_callback({
            "error": str(e)
        })

async def check_availability_for_calendar(function_name: str, tool_call_id: str, args: Dict, llm: Any, context: Any, result_callback: Any) -> None:
    """
    Vérifier la disponibilité d'un calendrier spécifique à une date donnée
    
    Args:
        function_name: The name of the function being called
        tool_call_id: The ID of the tool call
        args: Arguments containing date and calendar_id to check availability
        llm: The LLM service instance
        context: The context object
        result_callback: Callback to send results back to the LLM
    """
    try:
        # Parse the date and calendar_id from arguments
        date_str = args.get('date')
        calendar_id = args.get('calendar_id', 'primary')
        
        if not date_str:
            await result_callback({"available_slots": [], "error": "Aucune date fournie"})
            return

        # Parse date, handling relative references
        date = parse_relative_date(date_str)
        
        # If the parsed date is a weekend, inform the user
        if date.weekday() >= 5:  # Saturday or Sunday
            await result_callback({
                "date": date_str,
                "formatted_date": date.strftime("%A %d %B %Y").capitalize(),
                "available_slots": [],
                "is_today": date == get_current_time().date(),
                "is_weekday": False,
                "error": "Cette date tombe un week-end. La clinique est fermée."
            })
            return
                
        # Get calendar service
        service = get_calendar_service()
        
        # Try to get the calendar name
        calendar_name = "Calendrier principal"
        try:
            calendar_info = service.calendars().get(calendarId=calendar_id).execute()
            calendar_name = calendar_info.get('summary', 'Calendrier principal')
        except Exception:
            # If we can't get the calendar details, continue with the default name
            pass
        
        # Set time boundaries for the specified date
        time_min = datetime.datetime.combine(date, datetime.time.min).replace(tzinfo=TIMEZONE_PYTZ).isoformat()
        time_max = datetime.datetime.combine(date, datetime.time.max).replace(tzinfo=TIMEZONE_PYTZ).isoformat()
        
        # Get events from the calendar
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Define working hours (9 AM to 5 PM)
        working_hours_start = 9  # 9h
        working_hours_end = 17   # 17h
        slot_duration = 30       # 30 minutes per slot
        
        # Generate all possible slots
        all_slots = []
        for hour in range(working_hours_start, working_hours_end):
            for minute in [0, 30]:
                slot_time = f"{hour:02d}h{minute:02d}" if minute > 0 else f"{hour:02d}h"
                all_slots.append(slot_time)
        
        # Mark booked slots
        booked_slots = []
        for event in events:
            start = event['start'].get('dateTime')
            if start:
                start_time = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                # Convert to Paris time
                start_time = start_time.astimezone(TIMEZONE_PYTZ)
                slot = f"{start_time.hour:02d}h{start_time.minute:02d}" if start_time.minute > 0 else f"{start_time.hour:02d}h"
                booked_slots.append(slot)
        
        # Find available slots
        available_slots = [slot for slot in all_slots if slot not in booked_slots]
        
        # Format the date nicely for display in French
        formatted_date = date.strftime("%A %d %B %Y").capitalize()
        
        await result_callback({
            "date": date_str,
            "formatted_date": formatted_date,
            "calendar_id": calendar_id,
            "calendar_name": calendar_name,
            "available_slots": available_slots,
            "is_today": date == get_current_time().date(),
            "is_weekday": date.weekday() < 5
        })
        
    except Exception as e:
        await result_callback({"error": str(e)})

def get_calendar_function_schemas() -> List[FunctionSchema]:
    """
    Return the function schemas for Google Calendar integration
    
    Returns:
        List of FunctionSchema objects for calendar operations
    """
    get_current_date_schema = FunctionSchema(
        name="get_current_date",
        description="Obtenir la date et l'heure actuelles dans le fuseau horaire de Paris",
        properties={},
        required=[],
    )
    
    check_availability_schema = FunctionSchema(
        name="check_availability",
        description="Vérifier la disponibilité du médecin à une date donnée (comprend les dates relatives comme 'aujourd'hui', 'demain', etc.)",
        properties={
            "date": {
                "type": "string",
                "description": "La date pour vérifier la disponibilité (format JJ/MM/AAAA, ou relative comme 'aujourd'hui', 'demain', 'lundi prochain', etc.)",
            }
        },
        required=["date"],
    )
    
    check_availability_for_calendar_schema = FunctionSchema(
        name="check_availability_for_calendar",
        description="Vérifier la disponibilité d'un calendrier spécifique à une date donnée",
        properties={
            "date": {
                "type": "string",
                "description": "La date pour vérifier la disponibilité (format JJ/MM/AAAA, ou relative comme 'aujourd'hui', 'demain', 'lundi prochain', etc.)",
            },
            "calendar_id": {
                "type": "string",
                "description": "L'identifiant du calendrier à vérifier",
            }
        },
        required=["date"],
    )
    
    schedule_appointment_schema = FunctionSchema(
        name="schedule_appointment",
        description="Programmer un nouveau rendez-vous pour un patient",
        properties={
            "patient_name": {
                "type": "string",
                "description": "Le nom complet du patient",
            },
            "date": {
                "type": "string",
                "description": "La date du rendez-vous (format JJ/MM/AAAA, ou relative comme 'aujourd'hui', 'demain', 'lundi prochain', etc.)",
            },
            "time": {
                "type": "string",
                "description": "L'heure du rendez-vous (format HHhMM ou HH:MM, par exemple '14h30' ou '14:30')",
            },
            "reason": {
                "type": "string",
                "description": "La raison du rendez-vous",
            },
            "calendar_id": {
                "type": "string",
                "description": "L'identifiant du calendrier dans lequel programmer le rendez-vous (par défaut: 'primary')",
            }
        },
        required=["patient_name", "date", "time"],
    )
    
    cancel_appointment_schema = FunctionSchema(
        name="cancel_appointment",
        description="Annuler un rendez-vous existant",
        properties={
            "appointment_id": {
                "type": "string",
                "description": "L'identifiant du rendez-vous à annuler",
            },
            "patient_name": {
                "type": "string",
                "description": "Le nom complet du patient dont le rendez-vous doit être annulé",
            },
            "date": {
                "type": "string",
                "description": "La date du rendez-vous à annuler (format JJ/MM/AAAA, ou relative comme 'aujourd'hui', 'demain', etc.)",
            }
        },
        required=[],  # At least one of these should be provided, but handled in the function
    )
    
    list_calendars_schema = FunctionSchema(
        name="list_calendars",
        description="Récupérer la liste de tous les calendriers et sous-calendriers disponibles",
        properties={},
        required=[],
    )
    
    return [
        get_current_date_schema,
        check_availability_schema,
        check_availability_for_calendar_schema,
        schedule_appointment_schema,
        cancel_appointment_schema,
        list_calendars_schema
    ]

def register_calendar_functions(llm_service: Any) -> None:
    """
    Register all Google Calendar functions with the LLM service
    
    Args:
        llm_service: The OpenAI LLM service instance to register functions with
    """
    llm_service.register_function("get_current_date", get_current_date)
    llm_service.register_function("check_availability", check_availability)
    llm_service.register_function("check_availability_for_calendar", check_availability_for_calendar)
    llm_service.register_function("schedule_appointment", schedule_appointment)
    llm_service.register_function("cancel_appointment", cancel_appointment)
    llm_service.register_function("list_calendars", list_calendars) 