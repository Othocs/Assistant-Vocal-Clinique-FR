#!/usr/bin/env python3
"""
Script pour exécuter tous les tests de l'API Google Calendar
Ce script sert de point d'entrée pour tester toutes les fonctionnalités de l'API
"""

import os
import sys
import subprocess
import argparse

def print_header(message):
    """Affiche un message formaté comme en-tête"""
    print("\n" + "=" * 70)
    print(f"  {message}")
    print("=" * 70)

def run_command(command):
    """Exécute une commande et renvoie son statut de sortie"""
    print(f"\nExécution de: {' '.join(command)}")
    result = subprocess.run(command, capture_output=False)
    return result.returncode == 0

def main():
    """Fonction principale qui exécute tous les tests"""
    parser = argparse.ArgumentParser(description="Lancer les tests de l'API Google Calendar")
    parser.add_argument("--all", action="store_true", help="Exécuter tous les tests")
    parser.add_argument("--general", action="store_true", help="Exécuter les tests généraux")
    parser.add_argument("--subcalendars", action="store_true", help="Exécuter les tests des sous-calendriers")
    parser.add_argument("--create-calendar", action="store_true", help="Inclure le test de création de calendrier")
    
    args = parser.parse_args()
    
    # Si aucune option n'est spécifiée, montrer l'aide
    if not (args.all or args.general or args.subcalendars):
        parser.print_help()
        return
    
    # Vérifier que les scripts de test existent
    if not os.path.exists("test_calendar_functions.py"):
        print("Erreur: Le fichier test_calendar_functions.py n'existe pas.")
        return
        
    if not os.path.exists("test_subcalendars.py"):
        print("Erreur: Le fichier test_subcalendars.py n'existe pas.")
        return
    
    print_header("TESTS DE L'API GOOGLE CALENDAR")
    
    all_success = True
    
    # Exécuter les tests généraux
    if args.all or args.general:
        print_header("TESTS DES FONCTIONS GÉNÉRALES")
        success = run_command(["python", "test_calendar_functions.py"])
        all_success = all_success and success
    
    # Exécuter les tests de sous-calendriers
    if args.all or args.subcalendars:
        print_header("TESTS DES SOUS-CALENDRIERS")
        command = ["python", "test_subcalendars.py"]
        if args.create_calendar:
            command.append("--create-calendar")
        success = run_command(command)
        all_success = all_success and success
    
    # Afficher le résultat global
    print_header("RÉSULTAT GLOBAL")
    if all_success:
        print("✅ Tous les tests ont réussi!")
    else:
        print("❌ Certains tests ont échoué. Consultez les détails ci-dessus.")
    
    return 0 if all_success else 1

if __name__ == "__main__":
    sys.exit(main()) 