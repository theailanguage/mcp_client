#!/usr/bin/env python
"""
streamlit_client_stdio.py

This file implements a LangChain MCP client that:
  - Loads configuration from a JSON file specified by the THEAILANGUAGE_CONFIG environment variable.
  - Connects to one or more MCP servers defined in the config.
  - Loads available MCP tools from each connected server.
  - Uses the Google Gemini API (via LangChain) to create a React agent with access to all tools.
  - Runs an interactive chat loop where user queries are processed by the agent.

Detailed explanations:
  - Retries (max_retries=2): If an API call fails due to transient issues (e.g., timeouts), it will retry up to 2 times.
  - Temperature (set to 0): A value of 0 means fully deterministic output; increase this for more creative responses.
  - Environment Variable: THEAILANGUAGE_CONFIG should point to a config JSON that defines all MCP servers.
"""

import asyncio                        # For asynchronous operations
import os                             # To access environment variables and file paths
import sys                            # For system-specific parameters and error handling
import json                           # For reading and writing JSON data
from contextlib import AsyncExitStack # For managing multiple asynchronous context managers

# ---------------------------
# MCP Client Imports
# ---------------------------
from mcp import ClientSession, StdioServerParameters  # For managing MCP client sessions and server parameters
from mcp.client.stdio import stdio_client             # For establishing a stdio connection to an MCP server

# ---------------------------
# Agent and LLM Imports
# ---------------------------
from langchain_mcp_adapters.tools import load_mcp_tools  # Adapter to convert MCP tools to LangChain compatible tools
from langgraph.prebuilt import create_react_agent        # Function to create a prebuilt React agent using LangGraph
from langchain_google_genai import ChatGoogleGenerativeAI  # Wrapper for the Google Gemini API via LangChain

# ---------------------------
# Environment Setup
# ---------------------------
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from a .env file (e.g., GOOGLE_API_KEY)

# ---------------------------
# Custom JSON Encoder for LangChain objects
# ---------------------------
class CustomEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle non-serializable objects returned by LangChain.
    If the object has a 'content' attribute (such as HumanMessage or ToolMessage), serialize it accordingly.
    """
    def default(self, o):
        # Check if the object has a 'content' attribute
        if hasattr(o, "content"):
            # Return a dictionary containing the type and content of the object
            return {"type": o.__class__.__name__, "content": o.content}
        # Otherwise, use the default serialization
        return super().default(o)

# ---------------------------
# Function: read_config_json
# ---------------------------
def read_config_json():
    """
    Reads the MCP server configuration JSON.

    Priority:
      1. Try to read the path from the THEAILANGUAGE_CONFIG environment variable.
      2. If not set, fallback to a default file 'theailanguage_config.json' in the same directory.

    Returns:
        dict: Parsed JSON content with MCP server definitions.
    """
    # Attempt to get the config file path from the environment variable
    config_path = os.getenv("THEAILANGUAGE_CONFIG")

    if not config_path:
        # If environment variable is not set, use a default config file in the same directory as this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "theailanguage_config.json")
        print(f"⚠️  THEAILANGUAGE_CONFIG not set. Falling back to: {config_path}")

    try:
        # Open and read the JSON config file
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        # If reading fails, print an error and exit the program
        print(f"❌ Failed to read config file at '{config_path}': {e}")
        sys.exit(1)


# ---------------------------
# Main Function: run_agent
# ---------------------------
async def run_agent(query: str) -> str:
    """
    Connects to all MCP servers defined in the configuration, loads their tools, creates a unified React agent,
    and starts an interactive loop to query the agent.
    """
    # ---------------------------
    # Google Gemini LLM Instantiation
    # ---------------------------
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",             # Specify the Google Gemini model variant to use
        temperature=0,                            # Set temperature to 0 for deterministic responses
        max_retries=2,                            # Set maximum retries for API calls to 2 in case of transient errors
        google_api_key=os.getenv("GOOGLE_API_KEY")  # Retrieve the Google API key from environment variables
    )

    config = read_config_json()  # Load MCP server configuration from the JSON file
    mcp_servers = config.get("mcpServers", {})  # Retrieve the MCP server definitions from the config
    if not mcp_servers:
        print("❌ No MCP servers found in the configuration.")
        return

    tools = []  # Initialize an empty list to hold all the tools from the connected servers

    # Use AsyncExitStack to manage and cleanly close multiple asynchronous resources
    async with AsyncExitStack() as stack:
        # Iterate over each MCP server defined in the configuration
        for server_name, server_info in mcp_servers.items():
            print(f"\n🔗 Connecting to MCP Server: {server_name}...")

            # Create StdioServerParameters using the command and arguments specified for the server
            server_params = StdioServerParameters(
                command=server_info["command"],
                args=server_info["args"]
            )

            try:
                # Establish a stdio connection to the server using the server parameters
                read, write = await stack.enter_async_context(stdio_client(server_params))
                # Create a client session using the read and write streams from the connection
                session = await stack.enter_async_context(ClientSession(read, write))
                # Initialize the session (e.g., perform handshake or setup operations)
                await session.initialize()

                # Load the MCP tools from the connected server using the adapter function
                server_tools = await load_mcp_tools(session)

                # Iterate over each tool and add it to the aggregated tools list
                for tool in server_tools:
                    print(f"\n🔧 Loaded tool: {tool.name}")
                    tools.append(tool)

                print(f"\n✅ {len(server_tools)} tools loaded from {server_name}.")
            except Exception as e:
                # Handle any errors that occur during connection or tool loading for the server
                print(f"❌ Failed to connect to server {server_name}: {e}")

        # If no tools were loaded from any server, exit the function
        if not tools:
            print("❌ No tools loaded from any server. Exiting.")
            return

        # Create a React agent using the Google Gemini LLM and the list of aggregated tools
        agent = create_react_agent(llm, tools)

        # Invoke the agent asynchronously with the query as the input message
        response = await agent.ainvoke({"messages": query})

        # Format and print the agent's response as nicely formatted JSON
        print("\nResponse:")
        try:
            formatted = json.dumps(response, indent=2, cls=CustomEncoder)
            print(formatted)
        except Exception:
            # If JSON formatting fails, simply print the raw response
            print(str(response))
        
        # If the response is a dict with "messages" list, extract the last AIMessage's content
        if isinstance(response, dict) and "messages" in response:
            for message in reversed(response["messages"]):
                if hasattr(message, "content"):
                    return message.content
            return "⚠️ No AI response found in messages"

# ---------------------------
# Entry Point
# ---------------------------
if __name__ == "__main__":
    # Run the asynchronous run_agent function using asyncio's event loop
    asyncio.run(run_agent())

