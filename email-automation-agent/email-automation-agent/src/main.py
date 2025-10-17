#!/usr/bin/env python3
"""
Email Automation Agent - Main Entry Point

This script initializes and runs the email automation agent.
"""

import asyncio
import logging
from pathlib import Path

from email_agent.agent import EmailAgent
from email_agent.config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/agent.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main function to run the email automation agent."""
    try:
        # Load configuration
        config_path = Path("config/config.yaml")
        config = Config.load_from_file(config_path)
        
        # Initialize the email agent
        agent = EmailAgent(config)
        
        logger.info("Starting Email Automation Agent...")
        
        # Run the agent
        await agent.run()
        
    except Exception as e:
        logger.error(f"Error running email agent: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())