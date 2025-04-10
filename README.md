# 🚀 MCP Client with Gemini AI

[📢 Subscribe to The AI Language on YouTube!](https://youtube.com/@theailanguage?sub_confirmation=1)

Welcome! This project features multiple MCP clients integrated with **Google Gemini AI** to execute tasks via the **Model Context Protocol (MCP)** — with and without LangChain.

Happy building, and don’t forget to subscribe!  


## MCP Client Options

This repository includes **four MCP client options** for various use cases:

| Option | Client Script | LangChain | Config Support | Transport | Tutorial |
|--------|-------------------------------|------------|----------------|-----------|----------|
| 1 | `client.py` | ❌ | ❌ | STDIO | [Legacy Client](https://youtu.be/GAPncIfnDwg) |
| 2 | `langchain_mcp_client.py` | ✅ | ❌ | STDIO | [LangChain Client](https://youtu.be/hccNm88bk6w) |
| 3 | `langchain_mcp_client_wconfig.py` | ✅ | ✅ | STDIO | [Multi-Server](https://youtu.be/nCnBWVv2uTA) |
| 4 | `client_sse.py` | ❌ | ❌ | SSE (Loca & Web) | [SSE Client](https://youtu.be/s0YJNcT1XMA) |

If you want to add or reuse MCP Servers, check out [the MCP Servers repo](https://github.com/modelcontextprotocol/servers).

---

## ✪ Features

✅ Connects to an MCP server (STDIO or SSE)  
✅ Uses **Google Gemini AI** to interpret user prompts  
✅ Allows **Gemini to call MCP tools** via server  
✅ Executes tool commands and returns results  
✅ (Upcoming) Maintains context and history for conversations  

---

### Running the MCP Client

Choose the appropriate command for your preferred client:

- **Legacy STDIO** — `uv run client.py path/to/server.py`
- **LangChain STDIO** — `uv run langchain_mcp_client.py path/to/server.py`
- **LangChain Multi-Server STDIO** — `uv run langchain_mcp_client_wconfig.py path/to/config.json`
- **SSE Client** — `uv run client_sse.py sse_server_url`

### Project Structure

```
mcp-client-gemini/
├── client.py                        # Basic client (STDIO)
├── langchain_mcp_client.py         # LangChain + Gemini
├── langchain_mcp_client_wconfig.py # LangChain + config.json (multi-server)
├── client_sse.py                   # SSE transport client (local or remote)
├── .env                            # API key environment file
├── README.md                       # Project documentation
├── requirements.txt                # Dependency list
├── .gitignore                      # Git ignore rules
├── LICENSE                         # License information
```

### How It Works

1. You send a prompt:
   > Create a file named test.txt
2. The prompt is sent to **Google Gemini AI**.
3. Gemini uses available **MCP tools** to determine a response.
4. The selected tool is executed on the **connected server**.
5. The AI returns results and maintains **conversation context** (if supported).

## 🤝 Contributing

At this time, this project does **not accept external code contributions**.

This is to keep licensing simple and avoid any shared copyright.

You're very welcome to:
✅ Report bugs or request features (via GitHub Issues)  
✅ Fork the repo and build your own version  
✅ Suggest documentation improvements

If you'd like to collaborate in another way, feel free to open a discussion!

