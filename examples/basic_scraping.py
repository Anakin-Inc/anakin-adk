"""Basic scraping agent using Anakin + Google ADK.

Prerequisites:
    pip install anakin-adk anakin-cli
    export GOOGLE_API_KEY=your-key
"""

from google.adk.agents import Agent

from anakin_adk import AnakinToolkit

agent = Agent(
    model="gemini-2.5-pro",
    name="scraper",
    instruction=(
        "You are a web scraping assistant. When the user gives you a URL, "
        "scrape it and return a clean summary of the page content."
    ),
    tools=AnakinToolkit().get_tools(),
)

if __name__ == "__main__":
    # Quick test via the ADK dev UI:
    #   adk web
    # Or run directly:
    #   adk run .
    print(f"Agent '{agent.name}' ready with {len(agent.tools)} tools.")
    print("Run with: adk web")
