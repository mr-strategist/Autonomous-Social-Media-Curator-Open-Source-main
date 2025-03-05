from crewai import Agent
from ..tools.content_tools import ContentTools
from ..config.llm_config import get_llm

def get_content_creator() -> Agent:
    """Get the content creator agent"""
    return Agent(
        role='Content Creator',
        goal='Create and post engaging content to configured social media platforms',
        backstory=(
            "Expert content creator specializing in Dev.to, Mastodon, and Threads platforms. "
            "Creates engaging, platform-appropriate content and ensures successful posting."
        ),
        tools=[ContentTools()],
        llm=get_llm(),
        allow_delegation=False,
        verbose=True,
        instructions=(
            "Follow these steps exactly:\n"
            "1. Generate engaging content\n"
            "2. Use the ContentTools to:\n"
            "   - Generate and show the content for review\n"
            "   - Post to currently enabled platforms\n"
            "3. Report the actual posting results using ONLY the enabled platforms\n\n"
            "Important: ONLY post to platforms that are currently enabled and authenticated. "
            "Check platform_statuses to determine which platforms to use. "
            "DO NOT include platforms that are not enabled."
        )
    ) 