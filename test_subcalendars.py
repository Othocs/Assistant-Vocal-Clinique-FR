#!/usr/bin/env python3
"""
Script de test spécifique pour la fonctionnalité de lecture des sous-calendriers
Ce script se concentre sur le test et la démo de la nouvelle fonctionnalité de sous-calendriers
"""

import asyncio
import json
import sys
from typing import Dict, List

# Import des fonctions nécessaires
from google_calendar_integration import (
    list_calendars,
    check_availability_for_calendar,
    schedule_appointment,
    get_calendar_service
)

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

async def test_list_calendars():
    """Test la fonction list_calendars pour récupérer tous les calendriers et sous-calendriers"""
    print("\n=== TEST: Récupération de tous les calendriers et sous-calendriers ===")
    await list_calendars("list_calendars", "test_id", {}, None, {}, test_callback)
    
    if test_result.error:
        print(f"ERREUR: {test_result.error}")
        return False
    
    calendars = test_result.result.get('calendars', [])
    primary_id = test_result.result.get('primary_calendar_id')
    
    print(f"Nombre total de calendriers trouvés: {len(calendars)}")
    print(f"ID du calendrier principal: {primary_id}")
    
    # Affiche les détails de tous les calendriers trouvés
    for i, calendar in enumerate(calendars):
        is_primary = calendar.get('is_primary', False)
        primary_marker = "[PRINCIPAL]" if is_primary else ""
        print(f"\nCalendrier {i+1} {primary_marker}")
        print(f"  ID: {calendar.get('id')}")
        print(f"  Nom: {calendar.get('summary')}")
        print(f"  Description: {calendar.get('description')}")
        print(f"  Rôle d'accès: {calendar.get('access_role')}")
        print(f"  Fuseau horaire: {calendar.get('time_zone')}")
    
    return True

async def test_availability_for_subcalendar():
    """Test la vérification de disponibilité pour un sous-calendrier spécifique"""
    print("\n=== TEST: Vérification de disponibilité d'un sous-calendrier spécifique ===")
    
    # Récupère d'abord la liste des calendriers
    await list_calendars("list_calendars", "test_id", {}, None, {}, test_callback)
    
    if test_result.error:
        print(f"ERREUR: {test_result.error}")
        return False
    
    calendars = test_result.result.get('calendars', [])
    if not calendars:
        print("Aucun calendrier disponible pour le test")
        return False
    
    # Utilise le premier calendrier non-primaire si disponible, sinon utilise le premier calendrier
    test_calendar = None
    for calendar in calendars:
        if not calendar.get('is_primary', False):
            test_calendar = calendar
            break
    
    if not test_calendar:
        test_calendar = calendars[0]
    
    calendar_id = test_calendar.get('id')
    calendar_name = test_calendar.get('summary', 'Calendrier de test')
    
    print(f"Test avec le calendrier: {calendar_name} (ID: {calendar_id})")
    
    # Vérifie la disponibilité pour demain
    args = {
        "date": "demain",
        "calendar_id": calendar_id
    }
    
    await check_availability_for_calendar("check_availability_for_calendar", "test_id", args, None, {}, test_callback)
    
    if test_result.error:
        print(f"ERREUR: {test_result.error}")
        return False
    
    available_slots = test_result.result.get('available_slots', [])
    formatted_date = test_result.result.get('formatted_date', 'date inconnue')
    
    print(f"Disponibilité pour {calendar_name} le {formatted_date}:")
    if available_slots:
        print("Créneaux disponibles:")
        for i, slot in enumerate(available_slots):
            print(f"  {i+1}. {slot}")
    else:
        print("Aucun créneau disponible à cette date")
    
    return True

async def test_create_appointment_in_subcalendar():
    """Test la création d'un rendez-vous dans un sous-calendrier spécifique"""
    print("\n=== TEST: Création d'un rendez-vous dans un sous-calendrier ===")
    
    # Récupère d'abord la liste des calendriers
    await list_calendars("list_calendars", "test_id", {}, None, {}, test_callback)
    
    if test_result.error:
        print(f"ERREUR: {test_result.error}")
        return False
    
    calendars = test_result.result.get('calendars', [])
    if not calendars:
        print("Aucun calendrier disponible pour le test")
        return False
    
    # Utilise le premier calendrier non-primaire si disponible, sinon utilise le premier calendrier
    test_calendar = None
    for calendar in calendars:
        if not calendar.get('is_primary', False):
            test_calendar = calendar
            break
    
    if not test_calendar:
        test_calendar = calendars[0]
    
    calendar_id = test_calendar.get('id')
    calendar_name = test_calendar.get('summary', 'Calendrier de test')
    
    print(f"Test de création de rendez-vous dans: {calendar_name} (ID: {calendar_id})")
    
    # Vérifie d'abord la disponibilité
    args = {
        "date": "demain",
        "calendar_id": calendar_id
    }
    
    await check_availability_for_calendar("check_availability_for_calendar", "test_id", args, None, {}, test_callback)
    
    if test_result.error:
        print(f"ERREUR lors de la vérification de disponibilité: {test_result.error}")
        return False
    
    available_slots = test_result.result.get('available_slots', [])
    if not available_slots:
        print("Aucun créneau disponible pour le test de création de rendez-vous")
        return False
    
    # Crée un rendez-vous au premier créneau disponible
    appointment_args = {
        "patient_name": "Patient Test Sous-Calendrier",
        "date": "demain",
        "time": available_slots[0],
        "reason": "Test de rendez-vous dans un sous-calendrier",
        "calendar_id": calendar_id
    }
    
    await schedule_appointment("schedule_appointment", "test_id", appointment_args, None, {}, test_callback)
    
    if test_result.error or not test_result.success:
        print(f"ERREUR lors de la création du rendez-vous: {test_result.error or 'Échec sans message d erreur'}")
        return False
    
    appointment_id = test_result.result.get('appointment_id')
    formatted_date = test_result.result.get('formatted_date')
    time = test_result.result.get('time')
    
    print(f"Rendez-vous créé avec succès dans le calendrier {calendar_name}:"),
    print(f"  ID: {appointment_id}"),
    print(f"  Patient: Patient Test Sous-Calendrier"),
    print(f"  Date: {formatted_date}"),
    print(f"  Heure: {time}"),
    print(f"  Motif: Test de rendez-vous dans un sous-calendrier"),
    
    return True

async def create_subcalendar():
    """Démo: Création d'un nouveau sous-calendrier (à utiliser avec précaution, seulement si nécessaire)"""
    print("\n=== DÉMO: Création d'un nouveau sous-calendrier ===")
    
    try:
        service = get_calendar_service()
        
        # Définit les propriétés du nouveau calendrier
        calendar = {
            'summary': 'Spécialiste - Dermatologie',
            'description': 'Calendrier pour les rendez-vous de dermatologie',
            'timeZone': 'Europe/Paris'
        }
        
        # Crée le calendrier
        created_calendar = service.calendars().insert(body=calendar).execute()
        
        print(f"Nouveau sous-calendrier créé avec succès:")
        print(f"  ID: {created_calendar['id']}")
        print(f"  Nom: {created_calendar['summary']}")
        
        return True
    except Exception as e:
        print(f"ERREUR lors de la création du sous-calendrier: {str(e)}")
        return False

async def main():
    """Fonction principale qui exécute tous les tests"""
    print("=== TESTS DES FONCTIONNALITÉS DE SOUS-CALENDRIERS ===")
    
    # Récupère les arguments de ligne de commande
    create_calendar = "--create-calendar" in sys.argv
    
    # Exécute les tests principaux
    tests = [
        ("Récupération des calendriers", test_list_calendars),
        ("Vérification disponibilité sous-calendrier", test_availability_for_subcalendar),
        ("Création rendez-vous dans sous-calendrier", test_create_appointment_in_subcalendar)
    ]
    
    # Ajoute le test de création de calendrier si demandé explicitement
    if create_calendar:
        tests.append(("Création de sous-calendrier", create_subcalendar))
    
    results = {}
    
    for name, test_func in tests:
        print(f"\nExécution du test: {name}...")
        success = await test_func()
        results[name] = "✅ Succès" if success else "❌ Échec"
    
    # Affiche le résumé des tests
    print("\n=== RÉSUMÉ DES TESTS ===")
    for name, result in results.items():
        print(f"{name}: {result}")
    
    print("\n=== FIN DES TESTS ===")
    print("\nNote: Pour créer un nouveau sous-calendrier (à des fins de test uniquement), exécutez ce script avec l'option: --create-calendar")

if __name__ == "__main__":
    # Variables globales
    test_result = TestResult()
    
    # Exécution des tests
    asyncio.run(main()) 