# Assistant Clinique Vocal

Un assistant vocal IA français pour la gestion des rendez-vous médicaux, intégré avec Google Calendar et une base de données patient.

## Vue d'ensemble

Ce projet est un assistant vocal IA conversationnel conçu pour aider les patients à planifier des rendez-vous médicaux. L'assistant est capable de comprendre les demandes en français, de vérifier les disponibilités des médecins, de planifier des rendez-vous et de gérer les informations des patients.

## Fonctionnalités principales

- **Conversation vocale naturelle en français** : Interaction entièrement vocale avec le patient
- **Intégration Google Calendar** :
  - Vérification des disponibilités des médecins
  - Planification de rendez-vous
  - Annulation ou modification de rendez-vous existants
  - Gestion des sous-calendriers par médecin
- **Gestion des patients** :
  - Vérification des patients existants dans la base de données
  - Ajout de nouveaux patients
  - Mise à jour des informations des patients
- **Flux de conversation structuré** :
  - Comprendre le besoin médical
  - Identifier le médecin approprié
  - Trouver un créneau disponible
  - Collecter/vérifier les informations du patient
  - Finaliser le rendez-vous

## Technologies utilisées

- **Pipecat** : Framework pour la création d'agents IA vocaux
- **Google Calendar API** : Pour la gestion des rendez-vous
- **Supabase** : Base de données pour la gestion des informations patients
- **Daily.co** : API de communication en temps réel pour les appels audio
- **Deepgram** : Reconnaissance vocale (Speech-to-Text)
- **ElevenLabs** : Synthèse vocale (Text-to-Speech)
- **OpenAI** : Modèles LLM pour le traitement du langage naturel

## Structure du projet

```
VoccaAI-Technical-Test/
├── main.py                        # Script principal
├── runner.py                      # Configuration et lancement de l'application
├── functionCallingServices/
│   ├── google_calendar_integration.py  # Intégration avec Google Calendar
│   ├── client_functions.py        # Fonctions de gestion des patients
│   ├── supabase_client.py         # Client Supabase pour la base de données
│   └── credentials.json           # Identifiants Google API
├── token.pickle                   # Token d'authentification Google
├── .env                           # Variables d'environnement
└── README_TESTS.md                # Documentation des tests Google Calendar
```

## Installation

### Prérequis

- Python 3.8 ou supérieur
- Compte Google avec accès à l'API Google Calendar
- Compte Supabase pour la base de données
- Comptes pour les services API tiers (Deepgram, ElevenLabs/Cartesia, Daily.co)

### Étapes d'installation

1. Cloner le dépôt :

   ```
   git clone <repository-url>
   cd VoccaAI-Technical-Test
   ```

2. Installer les dépendances :

   ```
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib python-dateutil pytz supabase aiohttp python-dotenv loguru pipecat
   ```

3. Configurer les variables d'environnement dans le fichier `.env` :

   ```
   DAILY_SAMPLE_ROOM_URL=<your-daily-room-url>
   DAILY_API_KEY=<your-daily-api-key>
   DEEPGRAM_API_KEY=<your-deepgram-api-key>
   ELEVEN_LABS_API_KEY=<your-elevenlabs-api-key>
   SUPABASE_URL=<your-supabase-url>
   SUPABASE_KEY=<your-supabase-key>
   ```

4. Configurer l'authentification Google Calendar :
   - Placer votre fichier `credentials.json` dans le dossier `functionCallingServices/`
   - Au premier lancement, une fenêtre de navigateur s'ouvrira pour l'authentification

## Utilisation

Lancer l'assistant avec la commande suivante :

```
python main.py
```

L'assistant se connectera à la salle Daily.co spécifiée et attendra l'arrivée d'un participant pour commencer l'interaction.

## Flux de conversation

L'assistant suit un flux de conversation structuré pour guider le patient tout au long du processus de prise de rendez-vous :

1. **Démarrage de l'appel** :

   - Présentation brève : "Bonjour, clinique médicale de Paris !"
   - Question d'ouverture : "En quoi puis-je vous aider aujourd'hui?"

2. **Comprendre le besoin médical** :

   - Discussion pour comprendre la raison de la consultation
   - Collecte d'informations sur les symptômes ou le type de consultation

3. **Identifier le médecin approprié** :

   - Consultation de la liste des médecins disponibles
   - Proposition des médecins en fonction de leur spécialité

4. **Trouver un créneau disponible** :

   - Vérification des disponibilités du médecin choisi
   - Proposition de créneaux disponibles
   - Confirmation du créneau choisi

5. **Gestion des informations patient** :

   - Vérification si le patient existe déjà dans la base de données
   - Enregistrement d'un nouveau patient ou mise à jour des informations existantes

6. **Finalisation du rendez-vous** :
   - Résumé des détails du rendez-vous
   - Confirmation de la réservation
