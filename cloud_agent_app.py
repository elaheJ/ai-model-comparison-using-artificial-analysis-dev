"""Streamlit Community Cloud entry point for the checked-agent app.

Uses a hosted LLM configured in Streamlit Secrets; no model weights are loaded
into the web server. Local users can still run agent_app.py with Qwen.
"""
from model_compare.ui import main

main(agent=True, cloud=True)
