import asyncio
import json
import os
from typing import Dict, Any, List

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from mcp.server import Server
from mcp.types import Tool, TextContent

# Initialize FastAPI and MCP Server
app = FastAPI()

# Add CORS middleware to handle cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, adjust in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

mcp_server = Server("chat-saver")

# Path for the temporary file - explicitly using /tmp
TEMP_FILE_PATH = "/tmp/latest_chat.py"

@mcp_server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="save_chat",
            description="Save the latest chat message to a temporary Python file",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The chat message to save"
                    }
                },
                "required": ["message"]
            }
        ),
        Tool(
            name="get_chat_path",
            description="Get the path to the saved chat file",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    if name == "save_chat":
        message = arguments.get("message", "")
        try:
            with open(TEMP_FILE_PATH, "w") as f:
                f.write(f"# Latest chat message saved at {asyncio.get_event_loop().time()}\n\n")
                f.write(f"message = \"\"\"{message}\"\"\"\n\n")
                f.write("# You can access this message by importing this file\n")
                f.write("# Example: from latest_chat import message\n")
            return [TextContent(type="text", text=f"Successfully saved chat message to {TEMP_FILE_PATH}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error saving chat message: {str(e)}")]
    
    elif name == "get_chat_path":
        if os.path.exists(TEMP_FILE_PATH):
            return [TextContent(type="text", text=f"Latest chat file is at: {TEMP_FILE_PATH}")]
        else:
            return [TextContent(type="text", text="No chat has been saved yet.")]
    
    return [TextContent(type="text", text=f"Unknown tool: {name}")]

# Global variable to store pending messages
message_queues = set()

# SSE endpoints
@app.get("/sse")
async def sse_endpoint(request: Request):
    async def event_generator():
        message_queue = asyncio.Queue()
        message_queues.add(message_queue)
        try:
            while True:
                try:
                    message = await message_queue.get()
                    if message is None:
                        break
                    yield {"data": json.dumps(message)}
                except asyncio.CancelledError:
                    break
        finally:
            message_queues.remove(message_queue)
    
    return EventSourceResponse(event_generator())

@app.post("/message")
async def message_endpoint(request: Request):
    data = await request.json()
    response = await mcp_server.handle_request(data)
    
    # Broadcast response to all connected SSE clients
    if response and message_queues:
        for queue in message_queues:
            await queue.put(response)
    
    return Response(content=json.dumps(response) if response else "", media_type="application/json")

if __name__ == "__main__":
    import uvicorn
    print(f"MCP server starting. Messages will be saved to: {TEMP_FILE_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=8000)