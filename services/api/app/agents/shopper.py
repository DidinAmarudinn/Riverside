"""Shopper agent (ADK): answers in Bahasa Indonesia, checks stock, offers alternatives."""
from google.adk.agents import Agent

from ..config import settings

INSTRUCTION = """You are the in-store assistant for Radar Mart. Reply in friendly, informal Bahasa \
Indonesia. Use the tools to find the product and check stock. If it is out of stock, offer an in-stock \
alternative or a nearby branch. If the store does not sell it, say so and note the request."""

shopper_agent = Agent(
    name="shopper_agent",
    model=settings.gemini_model,
    instruction=INSTRUCTION,
    tools=[],  # search_products, check_stock — added when tools are implemented
)
