"""Multi-step agent: search the web, then scrape top results.

Demonstrates combining search_web and scrape_website tools
in a single agent for a search-then-extract workflow.

Prerequisites:
    pip install anakin-adk anakin-cli
    export GOOGLE_API_KEY=your-key
"""

from google.adk.agents import Agent

from anakin_adk import ScrapeWebsiteTool, SearchWebTool

agent = Agent(
    model="gemini-2.5-pro",
    name="search_and_scrape",
    instruction=(
        "You are a web research assistant. When the user asks a question:\n"
        "1. Use search_web to find relevant pages.\n"
        "2. Pick the most promising result URLs.\n"
        "3. Use scrape_website to extract detailed content from those pages.\n"
        "4. Synthesize the information into a clear answer."
    ),
    tools=[SearchWebTool(), ScrapeWebsiteTool()],
)

if __name__ == "__main__":
    print(f"Agent '{agent.name}' ready with search + scrape tools.")
    print("Run with: adk web")
