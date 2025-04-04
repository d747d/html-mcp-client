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
    
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Initial keep-alive comment
            yield ":\n\n"
            
            # Send heartbeats and wait for events
            while True:
                # Either process an event from the queue or send a heartbeat after timeout
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=25)
                    if event is None:  # None is our signal to close
                        break
                    yield f"data: {event}\n\n"
                except asyncio.TimeoutError:
                    # No events for a while, send a heartbeat
                    yield ":\n\n"
        except asyncio.CancelledError:
            logger.info(f"SSE connection {connection_id} cancelled")
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

# Message endpoint
@app.post("/messages")
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
            response["result"] = {
                "serverInfo": {
                    "name": "calculator-server",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        
        elif method == "tools/list":
            response["result"] = {
                "tools": tools
            }
        
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

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "connections": len(connections)
    }

# Run the server
if __name__ == "__main__":
    logger.info("Starting MCP server on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)