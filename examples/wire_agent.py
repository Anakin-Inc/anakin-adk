"""Wire agent: get structured data from real sites via pre-built actions.

The agent finds an action for the user's request (wire_discover), checks its
parameters (wire_catalog), and runs it (wire_read_action). Wire actions are
faster, cheaper and more reliable than scraping when one exists.

Prerequisites:
    pip install anakin-adk
    export GOOGLE_API_KEY=your-key
    export ANAKIN_API_KEY=ak-...   # free: https://anakin.io/signup
"""

from google.adk.agents import Agent

from anakin_adk import AnakinToolset

agent = Agent(
    model="gemini-2.5-pro",
    name="wire_agent",
    instruction=(
        "You get data from websites for the user.\n"
        "1. Call wire_discover with the user's intent.\n"
        "2. If an action fits, call wire_catalog with its catalog slug to read the exact params.\n"
        "3. Run it with wire_read_action and summarise the result.\n"
        "4. If no action fits, fall back to scrape_website.\n"
        "If a tool returns a hint (e.g. a link to connect an account), pass it to the user."
    ),
    tools=[
        AnakinToolset(tools=["wire_discover", "wire_catalog", "wire_read_action", "scrape_website"])
    ],
)

if __name__ == "__main__":
    print(f"Agent '{agent.name}' ready.")
    print("Run with: adk web")
