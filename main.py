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

# Import our Google Calendar integration
from google_calendar_integration import (
    get_calendar_function_schemas,
    register_calendar_functions,
    get_current_time,
    TIMEZONE
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

        llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o")

        # Register all calendar functions with the LLM service
        register_calendar_functions(llm)

        # Get calendar function schemas
        calendar_functions = get_calendar_function_schemas()
        
        # Create tools schema with calendar functions
        tools = ToolsSchema(standard_tools=calendar_functions)

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
        
        CAPACITÉS PRINCIPALES:
        1. Vérifier la disponibilité des médecins à des dates spécifiques
        2. Planifier de nouveaux rendez-vous
        3. Annuler ou reprogrammer des rendez-vous existants
        4. Répondre aux questions générales sur la clinique
        5. Consulter différents calendriers selon la spécialité médicale demandée
        
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
        
        GESTION DES CALENDRIERS:
        - La clinique possède plusieurs médecins et spécialistes
        - Vous pouvez consulter les différents calendriers et proposer le médecin approprié selon le motif de la visite
        - En cas de besoin urgent, vous pouvez vérifier la disponibilité de plusieurs médecins
        - Si le patient ne précise pas de préférence de médecin, proposez-lui le spécialiste le plus adapté à son besoin
        
        INSTRUCTIONS DE COMMUNICATION:
        - Soyez chaleureux et empathique - vous êtes la première interaction du patient avec la clinique
        - Utilisez un langage simple et évitez le jargon médical
        - Confirmez toujours les informations avec le patient avant de finaliser un rendez-vous
        - Adaptez votre style de communication selon le profil du patient (adulte, personne âgée, parent appelant pour un enfant)
        - Guidez patiemment l'appelant pour obtenir toutes les informations nécessaires sans paraître intrusif
        - Si le patient mentionne un symptôme inquiétant, suggérez poliment un rendez-vous plus rapproché
        
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
        
        CONSIGNES IMPÉRATIVES:
        - Vous devez vous exprimer UNIQUEMENT en français. N'utilisez JAMAIS l'anglais ou une autre langue.
        - Ne mentionnez jamais que vous êtes une IA ou un programme informatique - comportez-vous comme un réceptionniste humain
        - Si vous ne comprenez pas une demande, demandez poliment au patient de reformuler
        - Terminez toujours l'appel en résumant les informations du rendez-vous ou en confirmant qu'aucun rendez-vous n'a été pris
        """

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
        ]

        context = OpenAILLMContext(messages, tools)
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
            
            # Send an initial welcome message with current date information
            welcome_message = (
                f"Bonjour! Je suis votre assistant de la clinique médicale. Aujourd'hui nous sommes le {current_date}. "
            )
            
            await llm.push_frame(TTSSpeakFrame(welcome_message))
            
            # Queue context frame to prepare for user response
            await task.queue_frames([context_aggregator.user().get_context_frame()])

        runner = PipelineRunner()
        await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main()) 