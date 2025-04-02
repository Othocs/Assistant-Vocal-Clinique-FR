#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import asyncio
import os
import sys

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from runner import configure

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.google import GoogleLLMService
from pipecat.transports.services.daily import DailyParams, DailyTransport

# Import client functions
from client_functions import get_client_function_schemas, register_client_functions

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

video_participant_id = None


async def get_weather(function_name, tool_call_id, arguments, llm, context, result_callback):
    await llm.push_frame(TTSSpeakFrame("Let me check on that."))
    location = arguments["location"]
    await result_callback(f"The weather in {location} is currently 72 degrees and sunny.")


async def get_image(function_name, tool_call_id, arguments, llm, context, result_callback):
    logger.debug(f"!!! IN get_image {video_participant_id}, {arguments}")
    question = arguments["question"]
    await llm.request_image_frame(
        user_id=video_participant_id,
        function_name=function_name,
        tool_call_id=tool_call_id,
        text_content=question,
    )


async def main():
    async with aiohttp.ClientSession() as session:
        (room_url, token) = await configure(session)

        transport = DailyTransport(
            room_url,
            token,
            "Respond bot",
            DailyParams(
                audio_out_enabled=True,
                transcription_enabled=True,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
            ),
        )

        tts = CartesiaTTSService(
            api_key=os.getenv("CARTESIA_API_KEY"),
            voice_id="71a7ad14-091c-4e8e-a314-022ece01c121",  # British Reading Lady
        )

        llm = GoogleLLMService(api_key=os.getenv("GEMINI_API_KEY"), model="gemini-2.0-flash-001")
        
        # Register default functions
        llm.register_function("get_weather", get_weather)
        llm.register_function("get_image", get_image)
        
        # Register client database functions
        register_client_functions(llm)

        # Default function schemas
        weather_function = FunctionSchema(
            name="get_weather",
            description="Get the current weather",
            properties={
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA",
                },
                "format": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "The temperature unit to use. Infer this from the user's location.",
                },
            },
            required=["location", "format"],
        )
        
        get_image_function = FunctionSchema(
            name="get_image",
            description="Get an image from the video stream.",
            properties={
                "question": {
                    "type": "string",
                    "description": "The question that the user is asking about the image.",
                }
            },
            required=["question"],
        )
        
        # Get client database function schemas
        client_function_schemas = get_client_function_schemas()
        
        # Combine all function schemas
        all_function_schemas = [weather_function, get_image_function] + client_function_schemas
        tools = ToolsSchema(standard_tools=all_function_schemas)

        system_prompt = """\
You are a helpful assistant who converses with a user and answers questions. Respond concisely to general questions.

Your response will be turned into speech so use only simple words and punctuation.

You have access to various tools:
1. get_weather: Provides weather information for a specified location.
2. get_image: Answers questions about the user's video stream.
3. Client database functions:
   - add_client: Adds a new client to the database with first name, last name, email, and phone.
   - verify_client: Checks if a client exists in the database by email or phone.
   - update_client: Updates an existing client's information.
   - find_client_by_email: Finds a client using their email address.
   - find_client_by_phone: Finds a client using their phone number.
   - list_all_clients: Lists all clients in the database.

When interacting with clients, you should follow these guidelines:
- Use verify_client when the user wants to check if they are in the system
- Use add_client when the user wants to add a new client or register
- Use update_client when the user wants to update their information
- Use find_client_by_email or find_client_by_phone when looking up specific clients
- Use list_all_clients when an overview of all clients is needed

You can respond to questions about the weather using the get_weather tool.

You can answer questions about the user's video stream using the get_image tool. Some examples of phrases that \
indicate you should use the get_image tool are:
  - What do you see?
  - What's in the video?
  - Can you describe the video?
  - Tell me about what you see.
  - Tell me something interesting about what you see.
  - What's happening in the video?
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Say hello."},
        ]

        context = OpenAILLMContext(messages, tools)
        context_aggregator = llm.create_context_aggregator(context)

        pipeline = Pipeline(
            [
                transport.input(),
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
            ),
        )

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            global video_participant_id
            video_participant_id = participant["id"]
            await transport.capture_participant_transcription(participant["id"])
            await transport.capture_participant_video(video_participant_id, framerate=0)
            # Kick off the conversation.
            await task.queue_frames([context_aggregator.user().get_context_frame()])

        runner = PipelineRunner()

        await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())


