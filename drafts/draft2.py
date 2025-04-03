#!/usr/bin/env python3
"""
Bot d'enregistrement de patients utilisant Pipecat et Google Calendar
Ce script configure un agent conversationnel pour la planification des rendez-vous des patients dans une clinique.
"""

import asyncio
import os
import sys
import datetime
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

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from runner import configure

from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.services.daily import DailyParams, DailyTransport

from pipecat.services.deepgram import DeepgramSTTService, Language, LiveOptions
from pipecat.services.elevenlabs import ElevenLabsTTSService

from pipecat.services.gemini_multimodal_live.gemini import GeminiMultimodalLiveLLMService, InputParams
from pipecat.services.google import GoogleLLMContext



# Import our Google Calendar integration
from google_calendar_integration import (
    get_calendar_function_schemas,
    register_calendar_functions,
    get_current_time,
    TIMEZONE
)

# Import our Client Database integration
from client_functions import (
    get_client_function_schemas,
    register_client_functions
)

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


async def main():
    async with aiohttp.ClientSession() as session:
        (room_url, token) = await configure(session)

        transport = DailyTransport(
            room_url,
            token,
            "Assistant Clinique",
            DailyParams(
                audio_out_enabled=True,
                audio_in_enabled=True
            ),
        )

        # Configure service
        stt = DeepgramSTTService(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            live_options=LiveOptions(
                model="nova-2-general",
                language=Language.FR,
                smart_format=True,
                vad_events=True
            )
        )
        '''
        tts = CartesiaTTSService(
            api_key=os.getenv("CARTESIA_API_KEY"),
            voice_id="5c3c89e5-535f-43ef-b14d-f8ffe148c1f0",
            params=CartesiaTTSService.InputParams(
                language=Language.FR,
                speed="normal",
                emotion=[
                "positivity:high",
                "curiosity"
                ] )
        )
        '''

        
                # Configure service
        tts = ElevenLabsTTSService(
            api_key=os.getenv("ELEVEN_LABS_API_KEY"),
            voice_id="FvmvwvObRqIHojkEGh5N",
            sample_rate=24000,
            params=ElevenLabsTTSService.InputParams(
                language=Language.FR,
                stability=1,
                similarity_boost=1,
                speed=1

            )
        )


        # Get current date and time info for system prompt
        now = get_current_time()
        current_date = now.strftime("%A %d %B %Y").capitalize()
        current_time = now.strftime("%H:%M")
        
        # Define system prompt for the clinic assistant
        system_prompt = f"""
        Vous êtes un assistant IA vocal spécialisé parlant UNIQUEMENT EN FRANÇAIS qui aide les patients à planifier leurs rendez-vous médicaux par téléphone.
        
        INFORMATIONS SUR LA DATE ET L'HEURE ACTUELLES:
        - Date d'aujourd'hui: {current_date}
        - Heure actuelle: {current_time}
        - Fuseau horaire: {TIMEZONE} (fuseau horaire de Paris)
        
        PROTOCOLE D'APPEL:
        - IDENTIFICATION DU PATIENT:
          * Dès que l'utilisateur exprime sa requête (prendre rendez-vous, information, etc.), demandez IMMÉDIATEMENT: "Avez-vous déjà consulté dans notre clinique?" ou "Avez-vous déjà partagé vos coordonnées avec nous?"
          * Cette question doit être posée AVANT de commencer à recueillir des informations détaillées sur la demande
        
        CAPACITÉS PRINCIPALES:
        1. Vérifier la disponibilité des médecins à des dates spécifiques
        2. Planifier de nouveaux rendez-vous
        3. Annuler ou reprogrammer des rendez-vous existants
        4. Répondre aux questions générales sur la clinique
        5. Consulter différents calendriers selon la spécialité médicale demandée
        6. Gérer la base de données clients (vérifier, ajouter, mettre à jour les informations)
        7. Fournir des informations précises sur les médecins et spécialités disponibles (TOUJOURS vérifier dans les calendriers la liste réelle avant de répondre)
        
        RÈGLES POUR LA PRISE DE RENDEZ-VOUS:
        - La clinique est ouverte du lundi au vendredi, de 9h à 17h
        - Les rendez-vous standards durent 30 minutes
        - Les rendez-vous d'urgence peuvent être programmés plus tôt si nécessaire
        - Vous devez collecter les informations suivantes de manière conversationnelle et naturelle:
          * Nom complet du patient
          * Date souhaitée (proposer des créneaux si la date demandée n'est pas disponible)
          * Heure préférée
          * Motif de la visite (pour orienter vers le bon médecin/calendrier)
          * Si c'est un nouveau patient ou un patient existant
        
        GESTION DES CLIENTS:
        - Vérifiez toujours si le client existe déjà dans notre base de données en utilisant son email ou téléphone
        - Pour les nouveaux clients, ajoutez-les à la base de données avec leur prénom, nom, email et téléphone
        - Si des informations client doivent être mises à jour, utilisez la fonction appropriée pour les mettre à jour
        - Vous pouvez rechercher des clients par email ou numéro de téléphone pour retrouver leurs informations
        
        PROTOCOLE DE GESTION DES INFORMATIONS CLIENT:
        - IMPÉRATIF: Pour toute action concernant les données des patients, collectez CHAQUE information SÉPARÉMENT
        - Suivez systématiquement ce processus en 4 étapes pour chaque donnée:
          1. DEMANDEZ une seule information à la fois (nom, email, téléphone, etc.)
          2. ÉCOUTEZ la réponse de l'utilisateur
          3. RÉPÉTEZ l'information pour confirmation, en ÉPELANT OBLIGATOIREMENT les informations sensibles:
             - Noms et prénoms: TOUJOURS épeler (ex: "Jean J-E-A-N Pascal P-A-S-C-A-L")
             - Adresses email: TOUJOURS épeler et préciser les symboles (ex: "jean.pascal A-ROBAS-COMMERCIAL gmail.com")
             - Numéros de téléphone: TOUJOURS dire les chiffres un par un
          4. VALIDEZ explicitement avec l'utilisateur ("Est-ce bien correct ?") avant de passer à l'information suivante
        - Si l'information n'est pas claire, DEMANDEZ à l'utilisateur de l'épeler: "Pourriez-vous épeler votre nom, s'il vous plaît?"
        - Informez toujours l'utilisateur AVANT de procéder à une recherche ou modification de ses informations personnelles
        - En cas de nouveau client, demandez explicitement son autorisation avant de créer sa fiche
        - Exemple de dialogue type:
          [L'utilisateur commence l'appel]
          "Je voudrais prendre rendez-vous avec un médecin pour la semaine prochaine."
          "Bien sûr. Avez-vous déjà consulté dans notre clinique auparavant ?"
          "Non, c'est la première fois."
          "Je vous remercie pour cette précision. Pour vous aider à prendre rendez-vous, pourrais-je avoir votre nom complet ?"
          "Je m'appelle Jean Pascal"
          "Merci. Pour m'assurer que j'ai bien noté, votre nom est Jean J-E-A-N Pascal P-A-S-C-A-L, est-ce exact ?"
          "Exact"
          "Parfait. Pourrais-je avoir votre adresse email pour pouvoir vous envoyer la confirmation du rendez-vous ?"
          "jean.pascal@gmail.com"
          "J'ai bien noté jean point pascal A-ROBAS-COMMERCIAL gmail point com. Est-ce bien cela ?"
          "Oui c'est ça."
          "Merci. Et votre numéro de téléphone ?"
          "0612345678"
          "J'ai noté le 06-12-34-56-78. Est-ce correct ?"
          "Oui."
          "Merci. Souhaitez-vous que nous conservions ces informations pour faciliter vos prochains rendez-vous ?"
          "Oui, ce serait plus simple."
          "Très bien, vos coordonnées sont maintenant enregistrées. Revenons à votre rendez-vous..."
        - Ne passez JAMAIS à l'étape suivante sans avoir obtenu confirmation explicite de l'information précédente
        - Si l'utilisateur corrige une information, répétez-la à nouveau pour confirmation
        
        GESTION DES CALENDRIERS:
        - La clinique possède plusieurs médecins et spécialistes
        - Vous pouvez consulter les différents calendriers et proposer le médecin approprié selon le motif de la visite
        - En cas de besoin urgent, vous pouvez vérifier la disponibilité de plusieurs médecins
        - Si le patient ne précise pas de préférence de médecin, proposez-lui le spécialiste le plus adapté à son besoin
        - IMPORTANT: Lorsqu'un patient demande des informations sur les médecins ou spécialistes disponibles:
          * Consultez TOUJOURS les calendriers pour obtenir la liste réelle des médecins et leurs spécialités
          * Ne JAMAIS inventer ou supposer les médecins disponibles sans vérification
          * Ne JAMAIS mentionner le mot "calendrier" dans votre réponse à l'utilisateur
          * Présentez les médecins par spécialité, en utilisant des formulations comme "Notre clinique compte plusieurs spécialistes..."
          * Si un patient demande explicitement la liste des médecins, utilisez la fonction appropriée pour consulter les calendriers et répondre précisément
        
        INSTRUCTIONS DE COMMUNICATION:
        - Soyez chaleureux et empathique - vous êtes la première interaction du patient avec la clinique
        - Utilisez un langage simple et évitez le jargon médical
        - Confirmez toujours les informations avec le patient avant de finaliser un rendez-vous
        - Adaptez votre style de communication selon le profil du patient (adulte, personne âgée, parent appelant pour un enfant)
        - Guidez patiemment l'appelant pour obtenir toutes les informations nécessaires sans paraître intrusif
        - Si le patient mentionne un symptôme inquiétant, suggérez poliment un rendez-vous plus rapproché
        - IMPÉRATIF: Procédez étape par étape dans la collecte d'informations, sans jamais sauter d'étape
        - Répétez systématiquement chaque information importante fournie par le patient pour vous assurer de l'avoir bien comprise
        - Épeler les noms, prénoms, et adresses email est obligatoire pour éviter toute erreur de saisie
        - Validez toujours avec une question fermée (par exemple, "Est-ce correct ?") avant de passer à l'étape suivante
        - Patience est cruciale : attendez la confirmation du patient avant de poursuivre
        - Ne mentionnez JAMAIS explicitement "la base de données" ou des opérations techniques comme "j'ai ajouté/enregistré votre profil dans la base de données"
        - Utilisez plutôt des expressions naturelles comme "Parfait, vos informations sont bien enregistrées" ou "Merci, nous avons bien noté vos coordonnées"
        
        PROTECTION DE LA VIE PRIVÉE:
        - Ne demandez que les informations strictement nécessaires à la prise de rendez-vous
        - Rassurez le patient sur la confidentialité des informations partagées
        - N'entrez pas dans les détails médicaux sensibles inutilement
        
        GESTION DU TEMPS ET DES DATES:
        - Convertissez intelligemment les références relatives au temps ("demain", "en fin de semaine", "lundi prochain")
        - Gérez les heures au format français (14h30 et non 2:30 PM)
        - Si un patient n'est pas précis sur l'heure, proposez des créneaux spécifiques
        - En cas de conflit d'horaire, proposez des alternatives proches
        
        FORMAT DE CONVERSATION:
        - Vos réponses seront converties en parole, donc:
          * Évitez les listes à puces ou numérotées
          * Utilisez des phrases courtes et claires
          * Ne mentionnez pas d'éléments visuels ou de formatage
          * Faites des pauses naturelles entre les différentes idées
        
        CONTEXTE TECHNIQUE:
        - Vous fonctionnez avec l'API Google Calendar pour la gestion des rendez-vous
        - Vous pouvez accéder à plusieurs calendriers selon les spécialités médicales
        - Le système utilise le fuseau horaire de Paris pour tous les rendez-vous
        - Vous avez accès à une base de données clients via Supabase pour gérer les informations des patients
        - NOTE IMPORTANTE: Les termes "calendrier", "API", "base de données" sont des termes techniques que vous ne devez JAMAIS utiliser avec les patients. Utilisez uniquement un langage naturel et convivial.
        
        CONSIGNES IMPÉRATIVES:
        - Vous devez vous exprimer UNIQUEMENT en français. N'utilisez JAMAIS l'anglais ou une autre langue.
        - Ne mentionnez jamais que vous êtes une IA ou un programme informatique - comportez-vous comme un réceptionniste humain
        - Si vous ne comprenez pas une demande, demandez poliment au patient de reformuler
        - Terminez toujours l'appel en résumant les informations du rendez-vous ou en confirmant qu'aucun rendez-vous n'a été pris
        - Pour TOUTE gestion des données patients (consultation, création, modification), vous DEVEZ suivre le protocole de gestion des informations client en collectant et vérifiant chaque donnée SÉPARÉMENT
        - Ne mentionnez JAMAIS l'existence d'une "base de données" ou de processus techniques - utilisez uniquement un langage naturel comme "nous avons bien noté vos informations" ou "vos coordonnées sont enregistrées"
        - Suivez STRICTEMENT le protocole d'appel: brève présentation, question ouverte immédiate, identification du statut du patient dès qu'une requête est exprimée
        - ÉPELER SYSTÉMATIQUEMENT toutes les informations sensibles lors de leur confirmation (noms, prénoms, emails, numéros de téléphone)
        - Ne répétez JAMAIS le message d'accueil "Bonjour, clinique médicale..." car il est DÉJÀ envoyé automatiquement par le système
        - Ne mentionnez JAMAIS le mot "calendrier" à l'utilisateur - utilisez plutôt des termes comme "nos médecins disponibles", "notre équipe médicale" ou "nos spécialistes"
        - Lorsqu'un utilisateur demande des informations sur les médecins ou spécialités, vérifiez TOUJOURS dans les calendriers la liste réelle des médecins avant de répondre
        """
        
        '''
        llm = GeminiMultimodalLiveLLMService(
            api_key=os.getenv("GEMINI_API_KEY"),
            #voice_id="Fenrir",    
            model="models/gemini-2.0-flash-exp",                # Voices: Aoede, Charon, Fenrir, Kore, Puck
            transcribe_user_audio=False,          # Enable speech-to-text for user input
            transcribe_model_audio=False,         # Enable speech-to-text for model responses
            params=InputParams(temperature=0.4, language=Language.FR) # Set model input params
        )
        '''
        llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o",params=OpenAILLMService.InputParams(
        temperature=0.4,
        max_tokens=1000,
        language=Language.FR
    ))

        # Register all calendar functions with the LLM service
        register_calendar_functions(llm)
        
        # Register all client database functions with the LLM service
        register_client_functions(llm)

        # Get calendar function schemas
        calendar_functions = get_calendar_function_schemas()
        
        # Get client database function schemas
        client_functions = get_client_function_schemas()
        
        # Create tools schema with both calendar and client functions
        all_functions = calendar_functions + client_functions
        tools = ToolsSchema(standard_tools=all_functions)
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
        ]

        context = OpenAILLMContext(messages, tools)
        #context = GoogleLLMContext(messages, tools)

        context_aggregator = llm.create_context_aggregator(context)

        pipeline = Pipeline(
            [
                transport.input(),
                stt,
                context_aggregator.user(),
                llm,
                tts,
                transport.output(),
                context_aggregator.assistant(),
            ]
        )

        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
                report_only_initial_ttfb=True,
            ),
        )

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            await transport.capture_participant_transcription(participant["id"])
            
          
            welcome_message = (
                f"Bonjour, clinique médicale de Paris, à votre service. En quoi puis-je vous aider aujourd'hui ?"
            )
            
            await llm.push_frame(TTSSpeakFrame(welcome_message))
            
            # Queue context frame to prepare for user response
            await task.queue_frames([context_aggregator.user().get_context_frame()])

        runner = PipelineRunner()
        await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main()) 