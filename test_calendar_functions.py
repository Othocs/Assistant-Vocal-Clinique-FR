#!/usr/bin/env python3
"""
Script de test pour les fonctions d'API Google Calendar
Ce script teste toutes les fonctions d'API Google Calendar implémentées dans le projet d'assistant vocal
"""

import asyncio
import datetime
import json
from typing import Any, Dict, List

# Import des fonctions Google Calendar à tester
from google_calendar_integration import (
    get_current_date,
    check_availability,
    check_availability_for_calendar,
    schedule_appointment,
    cancel_appointment,
    list_calendars,
    get_current_time,
    parse_relative_date
)

class MockLLM:
    """Classe simulant l'instance LLM pour les tests"""
    async def push_frame(self, frame):
        print(f"[TTS Frame serait envoyé]: {frame.text}")

class TestResult:
    """Classe pour stocker les résultats de test"""
    def __init__(self):
        self.result = None
        self.success = False
        self.error = None

    def __str__(self):
        if self.error:
            return f"ERREUR: {self.error}"
        return json.dumps(self.result, indent=2, ensure_ascii=False)

async def test_callback(result: Dict) -> None:
    """Callback pour recevoir les résultats des fonctions"""
    test_result.result = result
    test_result.success = result.get('success', True) if isinstance(result, dict) else True
    test_result.error = result.get('error', None) if isinstance(result, dict) else None

async def test_get_current_date():
    """Test de la fonction get_current_date"""
    print("\n=== TEST: get_current_date ===")
    await get_current_date("get_current_date", "test_id", {}, mock_llm, {}, test_callback)
    print(test_result)
    return test_result.success

async def test_list_calendars():
    """Test de la fonction list_calendars"""
    print("\n=== TEST: list_calendars ===")
    await list_calendars("list_calendars", "test_id", {}, mock_llm, {}, test_callback)
    print(test_result)
    
    # Si la fonction réussit, on stocke les IDs des calendriers pour les tests suivants
    if not test_result.error and 'calendars' in test_result.result:
        global calendar_ids
        calendar_ids = [cal['id'] for cal in test_result.result['calendars']]
        print(f"Calendriers trouvés: {len(calendar_ids)}")
    
    return test_result.success

async def test_check_availability():
    """Test de la fonction check_availability"""
    print("\n=== TEST: check_availability ===")
    # Test avec la date de demain (pour éviter le week-end)
    tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%d/%m/%Y")
    await check_availability("check_availability", "test_id", {"date": "demain"}, mock_llm, {}, test_callback)
    print(test_result)
    
    # Stocke les créneaux disponibles pour les tests suivants
    if not test_result.error and 'available_slots' in test_result.result:
        global available_slots
        available_slots = test_result.result['available_slots']
        print(f"Créneaux disponibles trouvés: {len(available_slots)}")
    
    return test_result.success

async def test_check_availability_for_calendar():
    """Test de la fonction check_availability_for_calendar"""
    print("\n=== TEST: check_availability_for_calendar ===")
    
    # Si nous avons des calendriers, teste avec le premier calendrier
    calendar_id = calendar_ids[0] if calendar_ids else 'primary'
    args = {
        "date": "demain",
        "calendar_id": calendar_id
    }
    
    await check_availability_for_calendar("check_availability_for_calendar", "test_id", args, mock_llm, {}, test_callback)
    print(test_result)
    return test_result.success

async def test_schedule_appointment():
    """Test de la fonction schedule_appointment"""
    print("\n=== TEST: schedule_appointment ===")
    
    # Utilise un créneau disponible si on en a trouvé
    time_slot = available_slots[0] if available_slots else "14h00"
    
    # Si nous avons des calendriers, teste avec le premier calendrier
    calendar_id = calendar_ids[0] if calendar_ids else 'primary'
    
    args = {
        "patient_name": "Patient Test",
        "date": "demain",
        "time": time_slot,
        "reason": "Test automatique de l'API",
        "calendar_id": calendar_id
    }
    
    await schedule_appointment("schedule_appointment", "test_id", args, mock_llm, {}, test_callback)
    print(test_result)
    
    # Stocke l'ID du rendez-vous pour le test d'annulation
    if test_result.success and 'appointment_id' in test_result.result:
        global appointment_id
        appointment_id = test_result.result['appointment_id']
        print(f"Rendez-vous créé avec ID: {appointment_id}")
    
    return test_result.success

async def test_cancel_appointment():
    """Test de la fonction cancel_appointment"""
    print("\n=== TEST: cancel_appointment ===")
    
    # Si nous avons un ID de rendez-vous, l'utiliser pour annuler
    if appointment_id:
        args = {"appointment_id": appointment_id}
    else:
        args = {
            "patient_name": "Patient Test",
            "date": "demain"
        }
    
    await cancel_appointment("cancel_appointment", "test_id", args, mock_llm, {}, test_callback)
    print(test_result)
    return test_result.success

async def test_all_functions():
    """Exécute tous les tests des fonctions"""
    print("=== DÉBUT DES TESTS DES FONCTIONS GOOGLE CALENDAR ===")
    
    # Liste des fonctions à tester avec leur nom pour le rapport
    tests = [
        ("get_current_date", test_get_current_date),
        ("list_calendars", test_list_calendars),
        ("check_availability", test_check_availability),
        ("check_availability_for_calendar", test_check_availability_for_calendar),
        ("schedule_appointment", test_schedule_appointment),
        ("cancel_appointment", test_cancel_appointment)
    ]
    
    results = {}
    
    for name, test_func in tests:
        success = await test_func()
        results[name] = "✅ Succès" if success else "❌ Échec"
    
    # Affiche le résumé des tests
    print("\n=== RÉSUMÉ DES TESTS ===")
    for name, result in results.items():
        print(f"{name}: {result}")
    
    print("\n=== FIN DES TESTS ===")

if __name__ == "__main__":
    # Variables globales pour stocker les résultats intermédiaires
    test_result = TestResult()
    mock_llm = MockLLM()
    calendar_ids = []
    available_slots = []
    appointment_id = None
    
    # Exécution des tests
    asyncio.run(test_all_functions()) 