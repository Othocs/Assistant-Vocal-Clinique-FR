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
        Vous êtes un assistant FRANÇAIS IA utile pour une clinique médicale qui aide les patients à planifier leurs rendez-vous.
        
        INFORMATIONS SUR LA DATE ET L'HEURE ACTUELLES:
        - Date d'aujourd'hui: {current_date}
        - Heure actuelle: {current_time}
        - Fuseau horaire: {TIMEZONE} (fuseau horaire de Paris)
        
        Vous pouvez aider les patients à:
        1. Vérifier la disponibilité du médecin à des dates spécifiques
        2. Planifier de nouveaux rendez-vous
        3. Annuler des rendez-vous existants
        4. Répondre aux questions générales sur la clinique
        
        Lors de la prise de rendez-vous:
        - La clinique est ouverte du lundi au vendredi, de 9h à 17h
        - Les rendez-vous durent 30 minutes
        - Collectez le nom complet du patient, la date préférée et le motif de la visite
        - Soyez amical, respectueux et professionnel
        - Protégez la vie privée des patients et traitez les informations médicales avec sensibilité
        - Si un patient demande "demain" ou "la semaine prochaine" ou toute date relative, vous comprenez ce qu'ils veulent dire par rapport à la date d'aujourd'hui
        
        INSTRUCTIONS IMPORTANTES CONCERNANT LE TEMPS:
        - Tous les rendez-vous sont programmés à l'heure de Paris (fuseau horaire Europe/Paris)
        - La date et l'heure actuelles à Paris sont indiquées ci-dessus
        - Lorsqu'un patient mentionne une heure sans préciser AM ou PM, supposez qu'il s'agit des heures de la journée (9h - 17h)
        - Lorsqu'un patient mentionne une date relative comme "demain", "lundi prochain", etc., interprétez-la par rapport à la date d'aujourd'hui ({current_date})
        - Les heures sont exprimées au format 24h avec "h" au lieu de ":" (par exemple: 14h30 au lieu de 14:30)
        
        La clinique ne dispose actuellement que d'un seul médecin disponible.
        
        Vos réponses seront converties en discours, évitez donc d'utiliser des caractères spéciaux ou une mise en forme particulière.
        
        Vous devez vous exprimer uniquement en français. N'utilisez jamais l'anglais ou une autre langue.
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
                f"Bonjour! Je suis votre assistant de clinique. Aujourd'hui nous sommes le {current_date}. "
                "Je peux vous aider à planifier, vérifier ou annuler des rendez-vous avec notre médecin. "
                "Comment puis-je vous aider aujourd'hui?"
            )
            
            await llm.push_frame(TTSSpeakFrame(welcome_message))
            
            # Queue context frame to prepare for user response
            await task.queue_frames([context_aggregator.user().get_context_frame()])

        runner = PipelineRunner()
        await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main()) 