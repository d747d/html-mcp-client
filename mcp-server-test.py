from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import logging
import json
from typing import Dict, Any, AsyncGenerator

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp-server")

# Create FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Store active connections
connections = {}
connection_counter = 0

# Define calculator tools
tools = [
    {
        "name": "add",
        "description": "Add two numbers together",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "subtract",
        "description": "Subtract second number from first",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "multiply",
        "description": "Multiply two numbers",
        "inputSchema": {
            "type": "object", 
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "divide",
        "description": "Divide first number by second",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["a", "b"]
        }
    }
]

# Calculator functions
def calculate(operation, a, b):
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")

# Helper function to send a message to all connections
async def broadcast_message(message):
    if isinstance(message, dict):
        message = json.dumps(message)
    
    logger.info(f"Broadcasting message: {message}")
    for conn_id, queue in connections.items():
        try:
            await queue.put(message)
            logger.debug(f"Sent message to connection {conn_id}")
        except Exception as e:
            logger.error(f"Error sending to connection {conn_id}: {str(e)}")

# SSE endpoint
@app.get("/sse")
async def sse_endpoint(request: Request):
    global connection_counter
    connection_id = connection_counter
    connection_counter += 1
    
    logger.info(f"New SSE connection {connection_id}")
    
    # Create a queue for this connection
    queue = asyncio.Queue()
    connections[connection_id] = queue
    
    # Log connection information
    logger.info(f"Active connections: {len(connections)}")
    
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Initial keep-alive comment
            yield ":\n\n"
            
            # Send heartbeats and wait for events
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=25)
                    if event is None:  # None is our signal to close
                        logger.info(f"Closing connection {connection_id}")
                        break
                    logger.debug(f"Sending event to connection {connection_id}: {event}")
                    yield f"data: {event}\n\n"
                except asyncio.TimeoutError:
                    # No events for a while, send a heartbeat
                    yield ":\n\n"
        except Exception as e:
            logger.error(f"Error in SSE connection {connection_id}: {str(e)}")
        finally:
            # Clean up
            if connection_id in connections:
                del connections[connection_id]
            logger.info(f"SSE connection {connection_id} closed")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*"
        }
    )

# Message endpoint - handle messages at both /messages and root path
@app.post("/messages")
@app.post("/")
async def messages_endpoint(request: Request):
    try:
        # Get the request data
        data = await request.json()
        logger.info(f"Received message: {json.dumps(data)}")
        
        method = data.get("method")
        params = data.get("params", {})
        req_id = data.get("id")
        
        # Create response structure
        response = {"jsonrpc": "2.0"}
        if req_id is not None:
            response["id"] = req_id
        
        # Handle different method types
        if method == "initialize":
            logger.info("Handling initialize request")
            
            # Respond with server capabilities
            response["result"] = {
                "serverInfo": {
                    "name": "calculator-server",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
            
            # Start a task to notify about tools after a short delay
            # This will work even if the client doesn't send an "initialized" notification
            asyncio.create_task(auto_notify_tools())
            
            # Return response immediately
            result = JSONResponse(content=response)
            logger.info(f"Sent initialize response: {json.dumps(response)}")
            return result
        
        elif method == "initialized":
            logger.info("Received initialized notification")
            
            # After getting initialized notification, immediately send tools list changed notification
            # and queue up sending a tools list to client
            asyncio.create_task(notify_tools_list_changed())
            
            # Return empty response for notification
            return JSONResponse(content={})
        
        elif method == "tools/list":
            logger.info("Handling tools/list request")
            
            # Respond with tools list
            response["result"] = {
                "tools": tools
            }
            
            logger.info(f"Sending tools list response with {len(tools)} tools")
            return JSONResponse(content=response)
        
        elif method == "tools/call":
            logger.info("Handling tools/call request")
            
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            try:
                a = float(arguments.get("a", 0))
                b = float(arguments.get("b", 0))
                result = calculate(tool_name, a, b)
                
                response["result"] = {
                    "content": [
                        {
                            "type": "text",
                            "text": str(result)
                        }
                    ],
                    "isError": False
                }
                logger.info(f"Tool call successful: {tool_name}({a}, {b}) = {result}")
            except Exception as e:
                logger.error(f"Tool call error: {str(e)}")
                response["result"] = {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: {str(e)}"
                        }
                    ],
                    "isError": True
                }
        
        elif method == "close":
            # Handle close request
            response["result"] = {}
            # Signal all connections to close
            for conn_id in list(connections.keys()):
                await connections[conn_id].put(None)
        
        else:
            # Method not supported
            logger.warning(f"Unsupported method: {method}")
            response["error"] = {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        
        return JSONResponse(content=response)
    
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                },
                "id": None
            },
            status_code=500
        )

# Helper function to automatically notify about tools after initialization
async def auto_notify_tools():
    """Send tools notification even if client doesn't follow protocol correctly"""
    logger.info("Starting auto notification sequence for tools")
    
    # Wait a bit for the client to process the initialization
    await asyncio.sleep(1)
    
    # First, send a tools list changed notification
    notification = {
        "jsonrpc": "2.0",
        "method": "notifications/tools/list_changed"
    }
    
    logger.info("Sending automatic tools/list_changed notification")
    await broadcast_message(notification)
    
    # Wait a moment for the client to potentially request the tools list
    await asyncio.sleep(0.5)
    
    # If client still hasn't requested tools, send a direct list
    # with a fake response ID (this is non-standard but helps with problematic clients)
    tools_list = {
        "jsonrpc": "2.0",
        "id": 100,  # Using a likely unused ID
        "result": {
            "tools": tools
        }
    }
    
    logger.info(f"Sending direct tools list with {len(tools)} tools")
    await broadcast_message(tools_list)
    
    # For even more aggressive clients, also send a second message with ID 2
    # (which is typically what clients use for tools/list)
    tools_list2 = {
        "jsonrpc": "2.0", 
        "id": 2,  # Many clients use ID 2 for tools/list
        "result": {
            "tools": tools
        }
    }
    
    logger.info("Sending additional tools list with ID 2")
    await broadcast_message(tools_list2)

# Debug endpoint to view tools
@app.get("/debug/tools")
async def debug_tools():
    return {
        "tools": tools,
        "connections": len(connections)
    }

# Health check endpoint
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "connections": len(connections),
        "tools_count": len(tools)
    }

# Run the server
if __name__ == "__main__":
    logger.info("Starting MCP server on port 8000")
    logger.info(f"Server has {len(tools)} tools available")
    for tool in tools:
        logger.info(f" - {tool['name']}: {tool['description']}")
        
    uvicorn.run(app, host="0.0.0.0", port=8000)