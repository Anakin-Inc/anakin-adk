"""Basic scraping agent using Anakin + Google ADK.

Prerequisites:
    pip install anakin-adk
    export GOOGLE_API_KEY=your-key
    export ANAKIN_API_KEY=ak-...   # free: https://anakin.io/signup
"""

from google.adk.agents import Agent

from anakin_adk import ScrapeWebsiteTool

agent = Agent(
    model="gemini-2.5-pro",
    name="scraper",
    instruction=(
        "You are a web scraping assistant. When the user gives you a URL, "
        "scrape it and return a clean summary of the page content."
    ),
    tools=[ScrapeWebsiteTool()],
)

if __name__ == "__main__":
    # Quick test via the ADK dev UI:
    #   adk web
    # Or run directly:
    #   adk run .
    print(f"Agent '{agent.name}' ready.")
    print("Run with: adk web")
