import logging
from dotenv import load_dotenv
from crewai import Crew, Task
from .agents import get_database_manager, get_content_curator, get_content_creator
from .database.init_db import init_database as init_db
from .platforms.manager import PlatformManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main entry point"""
    try:
        load_dotenv()
        
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")

        # Initialize platform manager and check statuses
        platform_manager = PlatformManager()
        platform_statuses = platform_manager.check_all_statuses()
        logger.info(f"Platform statuses: {platform_statuses}")

        # Create content creation and posting task
        content_task = Task(
            description=(
                "Create and post engaging content by following these exact steps:\n"
                "1. Generate the following content:\n"
                "   - A post about the successful database verification\n"
                "   - Include the operational status and accessibility\n"
                "   - Make it engaging and informative\n"
                "2. Use the ContentPostingTool to:\n"
                "   - Show the content for review\n"
                "   - Get user approval\n"
                "   - Handle platform selection\n"
                "   - Post to selected platforms\n"
                "3. Report the posting results\n\n"
                "IMPORTANT: You must use the ContentPostingTool to handle the posting process."
            ),
            expected_output=(
                "A string containing a JSON object with the following structure:\n"
                "{\n"
                '    "content": "The generated content",\n'
                '    "posting_results": {\n'
                '        "platform1": {"success": true/false, "url": "post_url"},\n'
                '        "platform2": {"success": true/false, "url": "post_url"}\n'
                "    },\n"
                '    "status": "success/failure"\n'
                "}"
            ),
            agent=get_content_creator()
        )

        # Create crew with task
        crew = Crew(
            agents=[get_content_creator()],
            tasks=[content_task],
            verbose=True
        )

        result = crew.kickoff()
        return result

    except Exception as e:
        logger.error(f"Error running crew: {str(e)}")
        raise

if __name__ == "__main__":
    main() 