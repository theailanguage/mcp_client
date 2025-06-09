#!/usr/bin/env python
"""
langchain_mcp_client.py

This file implements an MCP client that:
  - Connects to an MCP server via a stdio connection.
  - Loads the available MCP tools using the adapter function load_mcp_tools.
  - Instantiates the ChatGoogleGenerativeAI model (Google Gemini) using your GOOGLE_API_KEY.
  - Creates a React agent using LangGraph’s prebuilt agent (create_react_agent) with the LLM and tools.
  - Runs an interactive asynchronous chat loop for processing user queries.

Detailed explanations:
  - Retries (max_retries=2): If an API call fails due to transient errors (e.g., network issues),
    the call will automatically be retried up to 2 times. Increase this if you experience temporary failures.
  - Temperature (set to 0): Controls randomness. A temperature of 0 yields deterministic responses.
    Higher values (e.g., 0.7) yield more creative, varied responses.
  - GOOGLE_API_KEY: Required for authentication with Google’s generative AI service.
  
Responses are printed as JSON using a custom encoder to handle non-serializable objects.
"""

import asyncio                        # For asynchronous operations
import os                             # To access environment variables
import sys                            # For command-line argument processing
import json                           # For pretty-printing JSON output
from contextlib import AsyncExitStack # Ensures all async resources are properly closed
from typing import Optional, List     # For type hints

# ---------------------------
# MCP Client Imports
# ---------------------------
from mcp import ClientSession, StdioServerParameters  # MCP session management and startup parameters
from mcp.client.stdio import stdio_client            # For connecting to the MCP server over stdio

# ---------------------------
# Agent and LLM Imports
# ---------------------------
from langchain_mcp_adapters.tools import load_mcp_tools  # Adapter to load MCP tools correctly
from langgraph.prebuilt import create_react_agent        # Prebuilt React agent from LangGraph
from langchain_google_genai import ChatGoogleGenerativeAI  # Google Gemini LLM wrapper

# ---------------------------
# Environment Setup
# ---------------------------
from dotenv import load_dotenv
load_dotenv()  # Loads environment variables from a .env file (e.g., GOOGLE_API_KEY)

# ---------------------------
# Custom JSON Encoder
# ---------------------------
class CustomEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles objects with a 'content' attribute.
    
    If an object has a 'content' attribute, it returns a dictionary with the object's type and its content.
    Otherwise, it falls back to the default encoding.
    """
    def default(self, o):
        if hasattr(o, "content"):
            return {"type": o.__class__.__name__, "content": o.content}
        return super().default(o)

# ---------------------------
# LLM Instantiation
# ---------------------------
# Create an instance of the Google Gemini LLM.
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",     # Gemini model to use
    temperature=0,              # 0 = deterministic output; increase for more creativity
    max_retries=2,              # Automatically retry API calls up to 2 times for transient errors
    google_api_key=os.getenv("GOOGLE_API_KEY")  # Google API key must be set in your environment or .env file
)

# ---------------------------
# MCP Server Script Argument
# ---------------------------
if len(sys.argv) < 2:
    print("Usage: python client_langchain_google_genai_bind_tools.py <path_to_server_script>")
    sys.exit(1)
server_script = sys.argv[1]

# ---------------------------
# MCP Server Parameters
# ---------------------------
# Configure parameters to launch the MCP server.
server_params = StdioServerParameters(
    command="python" if server_script.endswith(".py") else "node",
    args=[server_script],
)

# Global variable to hold the active MCP session.
# This is a simple holder with a "session" attribute for use by the tool adapter.
mcp_client = None

# ---------------------------
# Main Asynchronous Function: run_agent
# ---------------------------
async def run_agent():
    """
    Connect to the MCP server, load MCP tools, create a React agent, and run an interactive chat loop.
    
    Steps:
      1. Open a stdio connection to the MCP server.
      2. Create and initialize an MCP session.
      3. Store the session in a global holder (mcp_client) for tool access.
      4. Load MCP tools using load_mcp_tools.
      5. Create a React agent using create_react_agent with the LLM and loaded tools.
      6. Enter an interactive loop: for each user query, invoke the agent asynchronously using ainvoke,
         then print the response as formatted JSON using our custom encoder.
    """
    global mcp_client
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()  # Initialize MCP session
            # Set global mcp_client to a simple object holding the session.
            mcp_client = type("MCPClientHolder", (), {"session": session})()
            # Load MCP tools using the adapter; this handles awaiting and conversion.
            tools = await load_mcp_tools(session)
            # Create a React agent using the LLM and the loaded tools.
            agent = create_react_agent(llm, tools)
            print("MCP Client Started! Type 'quit' to exit.")
            while True:
                query = input("\nQuery: ").strip()
                if query.lower() == "quit":
                    break
                # The agent expects input as a dict with key "messages".
                response = await agent.ainvoke({"messages": query})
                # Format the response as JSON using the custom encoder.
                try:
                    formatted = json.dumps(response, indent=2, cls=CustomEncoder)
                except Exception as e:
                    formatted = str(response)
                print("\nResponse:")
                print(formatted)
    return

# ---------------------------
# Main Execution Block
# ---------------------------
if __name__ == "__main__":
    asyncio.run(run_agent())
