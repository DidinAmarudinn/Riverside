"""Store-manager agent (ADK): explains reorder advice and answers questions over the data."""
from google.adk.agents import Agent

from ..config import settings

INSTRUCTION = """You are Demand Radar, an inventory analyst for store managers. Answer in English. \
Always ground answers in tool results, and explain why the POS-only forecast and the Demand Radar \
forecast differ (unmet demand captured from shopper conversations)."""

manager_agent = Agent(
    name="manager_agent",
    model=settings.gemini_model,
    instruction=INSTRUCTION,
    tools=[],  # forecast comparison, reorder, gaps, bq query — added later
)
