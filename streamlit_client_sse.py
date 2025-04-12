#!/usr/bin/env python
"""
streamlit_client_sse.py

*********************************************
WARNING! - 
CODE NOT FULLY IMPLEMENTED, 
PLEASE USE AS A STARTING POINT TO EXPLORE 
*********************************************

This file implements the MCP client using SSE transport for the The AI Language project.
It is designed for integration with a Streamlit UI. It provides a helper function 
process_single_query(query, server_url) that:

  - Instantiates an MCP client,
  - Connects to an MCP server via SSE using the provided server URL,
  - Processes a query via the Gemini API (and MCP tool calls),
  - Cleans up the connection, and
  - Returns the response as a string.

Additionally, an optional interactive chat loop is provided for standalone testing.
"""

import asyncio
import os
import sys
import json
from typing import Optional

# ---------------------------
# MCP Client Imports
# ---------------------------
from mcp import ClientSession
from mcp.client.sse import sse_client

# ---------------------------
# Gemini SDK Imports
# ---------------------------
from google import genai
from google.genai import types
from google.genai.types import Tool, FunctionDeclaration, GenerateContentConfig

# ---------------------------
# Environment Setup
# ---------------------------
from dotenv import load_dotenv
load_dotenv()  # Loads env variables such as GEMINI_API_KEY

# ---------------------------
# Helper Functions for Schema and Tool Conversion
# ---------------------------
def clean_schema(schema):
    """
    Recursively remove 'title' fields from a JSON schema.
    """
    if isinstance(schema, dict):
        schema.pop("title", None)
        if "properties" in schema and isinstance(schema["properties"], dict):
            for key in schema["properties"]:
                schema["properties"][key] = clean_schema(schema["properties"][key])
    return schema

def convert_mcp_tools_to_gemini(mcp_tools):
    """
    Convert MCP tool definitions into Gemini-compatible tool declarations.
    """
    gemini_tools = []
    for tool in mcp_tools:
        parameters = clean_schema(tool.inputSchema)
        function_declaration = FunctionDeclaration(
            name=tool.name,
            description=tool.description,
            parameters=parameters
        )
        gemini_tool = Tool(function_declarations=[function_declaration])
        gemini_tools.append(gemini_tool)
    return gemini_tools

# ---------------------------
# MCPClient Class for SSE
# ---------------------------
class MCPClient:
    def __init__(self):
        """
        Initialize the MCP client.
        Sets up placeholders for the MCP session and connection context, 
        and instantiates the Gemini API client with the API key.
        """
        self.session: Optional[ClientSession] = None
        self._streams_context = None  # For managing the SSE connection lifecycle
        self._session_context = None  # For managing the MCP session
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found. Please add it to your .env file.")
        self.genai_client = genai.Client(api_key=gemini_api_key)

    async def connect_to_sse_server(self, server_url: str):
        """
        Connects to an MCP server using SSE.
        - Opens an SSE connection via sse_client.
        - Creates and initializes an MCP ClientSession.
        - Retrieves the available tools and converts them for Gemini.
        """
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()
        self._session_context = ClientSession(*streams)
        self.session = await self._session_context.__aenter__()
        await self.session.initialize()
        print("Initialized SSE client...")
        print("Listing tools...")
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])
        self.function_declarations = convert_mcp_tools_to_gemini(tools)

    async def cleanup(self):
        """
        Closes all open contexts to clean up network resources.
        """
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    async def process_query(self, query: str) -> str:
        """
        Processes a user query using the Gemini API and MCP tool calls.
        Steps:
          1. Formats the query as a Gemini Content object.
          2. Generates content through the Gemini API.
          3. If a tool call is requested, executes it and re-invokes Gemini.
          4. Returns the final aggregated text.
        """
        user_prompt_content = types.Content(
            role='user',
            parts=[types.Part.from_text(text=query)]
        )
        response = self.genai_client.models.generate_content(
            model='gemini-2.0-flash-001',
            contents=[user_prompt_content],
            config=GenerateContentConfig(
                tools=self.function_declarations,
            ),
        )
        final_text = []
        for candidate in response.candidates:
            if candidate.content.parts:
                for part in candidate.content.parts:
                    if part.function_call:
                        tool_name = part.function_call.name
                        tool_args = part.function_call.args
                        print(f"\n[Gemini requested tool call: {tool_name} with args {tool_args}]")
                        try:
                            result = await self.session.call_tool(tool_name, tool_args)
                            function_response = {"result": result.content}
                        except Exception as e:
                            function_response = {"error": str(e)}
                        function_response_part = types.Part.from_function_response(
                            name=tool_name,
                            response=function_response
                        )
                        function_response_content = types.Content(
                            role='tool',
                            parts=[function_response_part]
                        )
                        response = self.genai_client.models.generate_content(
                            model='gemini-2.0-flash-001',
                            contents=[
                                user_prompt_content,
                                part,
                                function_response_content,
                            ],
                            config=GenerateContentConfig(
                                tools=self.function_declarations,
                            ),
                        )
                        final_text.append(response.candidates[0].content.parts[0].text)
                    else:
                        final_text.append(part.text)
        return "\n".join(final_text)

# ---------------------------
# Helper Function for Streamlit UI Integration
# ---------------------------
async def process_single_query(query: str, server_url: str) -> str:
    """
    Processes a single query using the SSE client.
    
    Steps:
      - Instantiates an MCPClient.
      - Connects to the SSE server using the provided server URL.
      - Invokes the process_query method to process the query.
      - Cleans up the connection.
      - Returns the final response.
    
    Args:
        query (str): The user query.
        server_url (str): The SSE server URL.
    
    Returns:
        str: The processed response.
    """
    client = MCPClient()
    try:
        await client.connect_to_sse_server(server_url)
        response = await client.process_query(query)
        return response
    except Exception as e:
        return f"Error processing query via SSE: {e}"
    finally:
        await client.cleanup()

# ---------------------------
# Optional: Standalone Interactive Chat Loop for Testing
# ---------------------------
async def interactive_chat_loop():
    if len(sys.argv) < 2:
        print("Usage: python streamlit_client_sse.py <server_url>")
        sys.exit(1)
    server_url = sys.argv[1]
    client = MCPClient()
    try:
        await client.connect_to_sse_server(server_url)
        print("\nMCP SSE Client Ready! Type 'quit' to exit.")
        while True:
            query = input("\nQuery: ").strip()
            if query.lower() == "quit":
                break
            response = await client.process_query(query)
            print("\nResponse:")
            print(response)
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(interactive_chat_loop())