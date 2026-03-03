"""Deep research agent using Anakin + Google ADK.

This agent uses the deep_research tool to autonomously explore
the web and produce comprehensive reports on any topic.

Prerequisites:
    pip install anakin-adk anakin-cli
    export GOOGLE_API_KEY=your-key
"""

from google.adk.agents import Agent

from anakin_adk import DeepResearchTool

agent = Agent(
    model="gemini-2.5-pro",
    name="researcher",
    instruction=(
        "You are a research analyst. When the user asks about a topic, "
        "use the deep_research tool to produce a comprehensive report. "
        "After receiving the report, summarize the key findings and "
        "provide actionable insights."
    ),
    tools=[DeepResearchTool()],
)

if __name__ == "__main__":
    print(f"Agent '{agent.name}' ready.")
    print("Run with: adk web")
