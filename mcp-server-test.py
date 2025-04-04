# Helper function to notify about tools after initialization
async def notify_tools_after_initialization():
    """Send a notification to trigger the client to request the tools list"""
    logger.info("Waiting a moment before sending tools notification...")
    await asyncio.sleep(0.5)  # Small delay to ensure client has processed initialization
    
    # Send a notification that will trigger the client to request the tools list
    notification = {
        "jsonrpc": "2.0",
        "method": "notifications/tools/list_changed"
    }
    
    logger.info("Sending tools notification after initialization")
    await broadcast_notification(notification)
    
    # For debugging, also log the tools list
    logger.info(f"Tool list being broadcasted: {len(tools)} tools available")

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

# Enable detailed logging
logging.getLogger().setLevel(logging.DEBUG)

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
    
    # Log current connection state
    connection_count = len(connections)
    logger.info(f"Active connections: {connection_count}")
    for conn_id in connections:
        logger.info(f"- Connection {conn_id}")
    
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Initial keep-alive comment
            yield ":\n\n"
            
            # Send a test message to verify SSE is working
            test_message = json.dumps({"jsonrpc": "2.0", "method": "notifications/debug", "params": {"message": "SSE Connection Established"}})
            yield f"data: {test_message}\n\n"
            logger.info(f"Sent test message to connection {connection_id}")
            
            # Send heartbeats and wait for events
            while True:
                # Either process an event from the queue or send a heartbeat after timeout
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=25)
                    if event is None:  # None is our signal to close
                        logger.info(f"Received close signal for connection {connection_id}")
                        break
                    
                    logger.debug(f"Sending event to connection {connection_id}: {event}")
                    yield f"data: {event}\n\n"
                except asyncio.TimeoutError:
                    # No events for a while, send a heartbeat
                    logger.debug(f"Sending heartbeat to connection {connection_id}")
                    yield ":\n\n"
                except Exception as e:
                    logger.error(f"Error in event processing for connection {connection_id}: {str(e)}")
                    # Continue to keep the connection alive
        except asyncio.CancelledError:
            logger.info(f"SSE connection {connection_id} cancelled")
        except Exception as e:
            logger.error(f"Error in SSE connection {connection_id}: {str(e)}")
        finally:
            # Clean up
            if connection_id in connections:
                logger.info(f"Removing connection {connection_id} from active connections")
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

# Add these routes to handle both /messages and the root path for messaging
@app.post("/messages")
@app.post("/")  # Also handle messages at the root path for better compatibility
async def messages_endpoint(request: Request):
    try:
        # Get the request data
        data = await request.json()
        logger.debug(f"Received raw message: {json.dumps(data)}")
        
        method = data.get("method")
        params = data.get("params", {})
        req_id = data.get("id")
        
        logger.info(f"Processing method: {method}, id: {req_id}")
        
        # Create response structure
        response = {"jsonrpc": "2.0"}
        if req_id is not None:
            response["id"] = req_id
        
        # Handle different method types
        if method == "initialize":
            logger.debug("Handling initialize request")
            # Simple response with tools capability explicitly set to empty object
            # This follows the exact pattern in the client's initialization request
            response["result"] = {
                "serverInfo": {
                    "name": "calculator-server",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
            logger.debug(f"Initialize response: {json.dumps(response)}")
            
        elif method == "initialized":
            # Handle initialized notification (no response needed)
            logger.debug("Received initialized notification")
            
            # Since this notification doesn't expect a response, return an empty JSON object
            # but immediately after, check if we should send a tools/list notification
            asyncio.create_task(notify_tools_after_initialization())
            return JSONResponse(content={})
        
        elif method == "tools/list":
            logger.debug("Handling tools/list request")
            response["result"] = {
                "tools": tools
            }
            logger.debug(f"Tools list response: {json.dumps(response)}")
        
        
        elif method == "tools/call":
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
            except Exception as e:
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
            # Clean up connections
            for conn_id in list(connections.keys()):
                if conn_id in connections:
                    await connections[conn_id].put(None)  # Signal to close
        
        else:
            # Method not supported
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

# Helper function to broadcast a notification to all connected clients
async def broadcast_notification(notification):
    """
    Send a notification to all connected clients.
    
    Args:
        notification: Either a dict or a string containing the JSON notification
    """
    if isinstance(notification, dict):
        json_notification = json.dumps(notification)
    else:
        json_notification = notification
        
    logger.info(f"Broadcasting notification: {json_notification}")
    
    if not connections:
        logger.warning("No active connections to broadcast to")
        return
        
    for conn_id, queue in connections.items():
        logger.debug(f"Sending to connection {conn_id}")
        try:
            await queue.put(json_notification)
        except Exception as e:
            logger.error(f"Error sending to connection {conn_id}: {str(e)}")

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "connections": len(connections)
    }

# Helper function to send initial tools info after connection
async def send_initial_tools_info(queue):
    # Wait a short time to ensure connection is established
    await asyncio.sleep(1)
    
    try:
        # Send tools list as a special message
        tools_info = {
            "jsonrpc": "2.0",
            "method": "notifications/tools/list_changed"
        }
        logger.info("Sending initial tools notification to new connection")
        await queue.put(json.dumps(tools_info))
    except Exception as e:
        logger.error(f"Error sending initial tools info: {str(e)}")

# Add a debug endpoint to show available tools
@app.get("/debug/tools")
async def debug_tools():
    connections_info = {conn_id: queue.qsize() for conn_id, queue in connections.items()}
    return {
        "tools": tools,
        "connections": connections_info,
        "connection_count": len(connections)
    }

# Run the server
if __name__ == "__main__":
    logger.info("Starting MCP server on port 8000")
    logger.info(f"Server has {len(tools)} tools available:")
    for tool in tools:
        logger.info(f" - {tool['name']}: {tool['description']}")
    uvicorn.run(app, host="0.0.0.0", port=8000)