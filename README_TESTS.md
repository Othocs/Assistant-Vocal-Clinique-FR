# Tests des fonctionnalités Google Calendar

Ce dossier contient les scripts de test pour vérifier toutes les fonctionnalités d'intégration de Google Calendar dans le projet d'assistant vocal français pour la prise de rendez-vous.

## Objectifs

Ces tests ont été développés pour :

1. Vérifier le bon fonctionnement de toutes les fonctions d'API Google Calendar
2. Tester spécifiquement la nouvelle fonctionnalité de gestion des sous-calendriers
3. Servir de documentation sur l'utilisation des différentes fonctions
4. Aider au développement de nouvelles fonctionnalités

## Scripts disponibles

Le projet inclut les scripts de test suivants :

- `run_tests.py` : Script principal pour lancer tous les tests
- `test_calendar_functions.py` : Teste toutes les fonctions de base de l'API Google Calendar
- `test_subcalendars.py` : Teste spécifiquement les fonctionnalités liées aux sous-calendriers

## Comment exécuter les tests

### Prérequis

Avant d'exécuter les tests, assurez-vous que :

1. Les fichiers de configuration Google Calendar existent et sont valides :

   - `credentials.json` : Fichier de configuration Google API
   - `token.pickle` : Fichier de token d'authentification (sera créé automatiquement si nécessaire)

2. Toutes les dépendances sont installées :
   ```
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib python-dateutil pytz
   ```

### Exécution des tests

Vous pouvez exécuter les tests de plusieurs façons :

1. **Tous les tests** :

   ```
   python run_tests.py --all
   ```

2. **Uniquement les tests généraux** :

   ```
   python run_tests.py --general
   ```

3. **Uniquement les tests de sous-calendriers** :

   ```
   python run_tests.py --subcalendars
   ```

4. **Création d'un sous-calendrier** (à utiliser avec précaution) :

   ```
   python run_tests.py --subcalendars --create-calendar
   ```

5. **Tests individuels** :
   ```
   python test_calendar_functions.py
   python test_subcalendars.py
   ```

## Fonctionnalités testées

### Tests généraux (`test_calendar_functions.py`)

- `get_current_date` : Récupération de la date et heure actuelles
- `list_calendars` : Listage de tous les calendriers disponibles
- `check_availability` : Vérification des disponibilités à une date donnée
- `schedule_appointment` : Création d'un rendez-vous
- `cancel_appointment` : Annulation d'un rendez-vous existant

### Tests de sous-calendriers (`test_subcalendars.py`)

- Récupération de tous les sous-calendriers
- Vérification de disponibilité dans un sous-calendrier spécifique
- Création d'un rendez-vous dans un sous-calendrier spécifique
- (Optionnel) Création d'un nouveau sous-calendrier

## Résultat des tests

Chaque test affiche :

- Un résumé des opérations effectuées
- Les données récupérées ou envoyées
- Les erreurs éventuelles
- Un statut final (succès/échec)

Le script principal (`run_tests.py`) fournit un résumé global de tous les tests exécutés.

## Dépannage

### Problèmes d'authentification

Si vous rencontrez des problèmes d'authentification :

1. Supprimez le fichier `token.pickle`
2. Relancez les tests, une fenêtre de navigateur s'ouvrira pour vous permettre de vous authentifier
3. Après authentification, un nouveau fichier `token.pickle` sera créé

### Problèmes de permissions

Si vous rencontrez des erreurs de permission lors de la création ou modification de rendez-vous :

1. Vérifiez que le compte Google utilisé a les permissions nécessaires sur les calendriers
2. Vérifiez que les scopes d'API dans `credentials.json` incluent l'accès en écriture
