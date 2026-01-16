from arcadepy import AsyncArcade
from dotenv import load_dotenv
from google.adk import Agent, Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService, Session
from google_adk_arcade.tools import get_arcade_tools
from google.genai import types
from human_in_the_loop import auth_tool, confirm_tool_usage

import os

load_dotenv(override=True)


async def main():
    app_name = "my_agent"
    user_id = os.getenv("ARCADE_USER_ID")

    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    client = AsyncArcade()

    agent_tools = await get_arcade_tools(
        client, toolkits=["Zoom"]
    )

    for tool in agent_tools:
        await auth_tool(client, tool_name=tool.name, user_id=user_id)

    agent = Agent(
        model=LiteLlm(model=f"openai/{os.environ["OPENAI_MODEL"]}"),
        name="google_agent",
        instruction="# Introduction
Welcome to the Zoom Meeting Assistant, an AI agent designed to help you manage your Zoom meetings more effectively. Whether you need to retrieve meeting invitations or check your upcoming meetings, this agent will streamline the process and provide you with the necessary information with ease.

# Instructions
1. Determine user requests related to Zoom meetings.
2. Use the appropriate tools based on the request type:
   - To view upcoming meetings, utilize the `Zoom_ListUpcomingMeetings` tool.
   - To fetch a specific meeting invitation, use the `Zoom_GetMeetingInvitation` tool with the provided meeting ID.
3. Process the responses and provide clear and concise information to the user.

# Workflows

## Workflow 1: List Upcoming Meetings
1. **User Request**: The user asks to see their upcoming meetings.
2. **Tool**: Use `Zoom_ListUpcomingMeetings` to retrieve the meetings.
3. **Response**: Present the list of upcoming meetings to the user.

## Workflow 2: Retrieve Meeting Invitation
1. **User Request**: The user specifies a meeting ID for which they would like to retrieve the invitation note.
2. **Tool**: Use `Zoom_GetMeetingInvitation` with the provided `meeting_id`.
3. **Response**: Present the meeting invitation note to the user.",
        description="An agent that uses Zoom tools provided to perform any task",
        tools=agent_tools,
        before_tool_callback=[confirm_tool_usage],
    )

    session = await session_service.create_session(
        app_name=app_name, user_id=user_id, state={
            "user_id": user_id,
        }
    )
    runner = Runner(
        app_name=app_name,
        agent=agent,
        artifact_service=artifact_service,
        session_service=session_service,
    )

    async def run_prompt(session: Session, new_message: str):
        content = types.Content(
            role='user', parts=[types.Part.from_text(text=new_message)]
        )
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.content.parts and event.content.parts[0].text:
                print(f'** {event.author}: {event.content.parts[0].text}')

    while True:
        user_input = input("User: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        await run_prompt(session, user_input)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())