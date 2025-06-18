# HTML MCP Client

A lightweight, self-contained web-based client for the Model Context Protocol (MCP) that connects AI models with tools and services. Built as a single HTML file with no dependencies or build process required.

## Features

### 🔧 **MCP Integration**
- Full Model Context Protocol support via Server-Sent Events (SSE)
- Real-time tool discovery and execution
- JSON-RPC 2.0 compliant communication
- Tool approval workflow (manual or auto-approve)

### 🤖 **AI Model Support**
- Integration with OpenRouter API for access to 100+ AI models
- Support for both free and premium models
- Automatic model context limit detection and tracking
- Real-time token usage monitoring with visual indicators

### 📎 **File Attachments**
- Image support (PNG, JPEG, WebP) with preview
- PDF document support
- Drag-and-drop file upload
- Smart file size limits (10MB per file, 50MB total)

### 🎨 **User Interface**
- Clean, responsive design with dark/light theme support
- Collapsible sidebar panels for tools, connection, and settings
- Real-time typing indicators and connection status
- Conversation management with clear/export options

### ⚡ **Performance & Security**
- Optimized DOM manipulation with DocumentFragment batching
- Token count caching with LRU eviction
- Memory leak prevention with proper event cleanup
- Secure API key storage (session-only)
- Input validation and XSS protection
- Production-safe logging

## Quick Start

### 1. Download and Open
```bash
# Clone the repository
git clone https://github.com/your-username/html-mcp-client.git
cd html-mcp-client

# Open in browser (no server required!)
open mcp-client-webapp.html
```

### 2. Set Up OpenRouter (Optional)
- Visit [OpenRouter](https://openrouter.ai) to get an API key for premium models
- Or use free models without an API key

### 3. Connect to MCP Server
- Start your MCP server (default: `http://localhost:8000/sse`)
- Enter server URL and message endpoint in the connection panel
- Click "Connect" to establish connection

## Configuration

### OpenRouter Setup
1. **Get API Key**: Sign up at [openrouter.ai](https://openrouter.ai) for premium models
2. **Configure**: Enter your API key in Settings → OpenRouter API Key
3. **Select Model**: Choose from 100+ available models (free and premium)

### MCP Server Connection
- **Server URL**: Your MCP server endpoint (e.g., `http://localhost:8000/sse`)
- **Message Endpoint**: Message handling path (default: `/messages`)
- **Connection Mode**: Choose how to handle CORS (see CORS section below)
- **Auto-approve Tools**: Enable to automatically execute tool calls

### CORS Handling
Due to browser security, connecting to MCP servers may require CORS configuration:

**Direct Mode** (default):
- Requires MCP server to send CORS headers
- Add to your MCP server: `Access-Control-Allow-Origin: *`

**CORS Proxy Mode**:
- Uses allorigins.win public proxy (automatic)
- No server configuration needed
- May have rate limits

**Custom Proxy Mode**:
- Use your own CORS proxy server
- Run the included `cors-proxy-example.js`
- Configure proxy URL in settings

### Customization
- **System Prompt**: Customize the AI assistant's behavior
- **Theme**: Toggle between light and dark modes
- **Context Tracking**: Visual token usage with model-specific limits

## MCP Server Examples

### Python MCP Server with CORS
```python
# Example MCP server setup with CORS support
from mcp import Server
import asyncio

server = Server("example-server")

@server.tool("get_weather")
async def get_weather(location: str) -> str:
    return f"Weather in {location}: Sunny, 72°F"

if __name__ == "__main__":
    # Enable CORS for web clients
    asyncio.run(server.run_sse(
        host="localhost", 
        port=8000,
        cors_origins=["*"]  # Allow all origins for development
    ))
```

### CORS Proxy Server
```bash
# Run the included CORS proxy
node cors-proxy-example.js 3001

# Then configure client:
# Connection Mode: Custom Proxy
# Custom Proxy URL: http://localhost:3001/proxy
```

### Supported MCP Servers
- [mcp-server-filesystem](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem) - File system operations
- [mcp-server-git](https://github.com/modelcontextprotocol/servers/tree/main/src/git) - Git repository management
- [mcp-server-github](https://github.com/modelcontextprotocol/servers/tree/main/src/github) - GitHub API integration
- [mcp-server-postgres](https://github.com/modelcontextprotocol/servers/tree/main/src/postgres) - PostgreSQL database access

## Security Features

### API Key Protection
- Session-only storage (keys don't persist after browser close)
- No localStorage exposure of sensitive credentials
- Secure transmission over HTTPS in production

### Input Validation
- URL validation with protocol and network restrictions
- File type and size validation
- Message length limits to prevent DoS
- XSS protection with HTML sanitization

### Production Safety
- Automatic production mode detection
- Sensitive logging disabled in production
- Content Security Policy ready
- Error message sanitization

## Performance Optimizations

### Memory Management
- Chat history pruning (500 message limit)
- Token count caching with LRU eviction
- Event listener cleanup prevention
- Attachment size limits

### DOM Efficiency
- DocumentFragment for batch updates
- Lazy loading for images
- Optimized scrolling with requestAnimationFrame
- Minimal reflows and repaints

### Network Optimization
- Request debouncing (300ms)
- File upload chunking for large files
- Connection keepalive management
- Error retry mechanisms

## Browser Compatibility

- **Modern Browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Required Features**: ES6, Fetch API, Server-Sent Events, File API
- **Mobile**: Full responsive support for tablets and phones

## Development

### Architecture
- **Single File**: Complete application in `mcp-client-webapp.html`
- **No Build Process**: Open directly in browser
- **Vanilla JavaScript**: No frameworks or dependencies
- **CSS Custom Properties**: Theme system with CSS variables

### Code Structure
- `MCPClient` class: Main application controller
- Security layer: Input validation and sanitization
- Performance layer: Caching and optimization
- UI components: Modular interface elements

### Contributing
1. Fork the repository
2. Make your changes to `mcp-client-webapp.html`
3. Test in multiple browsers
4. Submit a pull request

## Troubleshooting

### Connection Issues
- **CORS Errors**: Use one of the CORS solutions (proxy mode, custom proxy, or server CORS headers)
- **SSL Mixed Content**: Use HTTPS for both client and server in production
- **Port Conflicts**: Check if MCP server port is available
- **Proxy Issues**: Verify proxy server is running and URL is correct

### Performance Issues
- **Memory Usage**: Enable chat history pruning in settings
- **Large Files**: Reduce attachment sizes or use file chunking
- **Slow Responses**: Check network connectivity and server performance

### Model Issues
- **API Limits**: Check OpenRouter usage limits and billing
- **Context Overflow**: Monitor token usage and clear conversation when needed
- **Tool Errors**: Verify MCP server tool implementations

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related Projects

- [Model Context Protocol](https://modelcontextprotocol.io/) - Official MCP specification
- [OpenRouter](https://openrouter.ai/) - AI model API aggregator
- [MCP Servers](https://github.com/modelcontextprotocol/servers) - Official MCP server implementations

## Support

- **Issues**: [GitHub Issues](https://github.com/your-username/html-mcp-client/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/html-mcp-client/discussions)
- **MCP Community**: [MCP Discord](https://discord.gg/modelcontextprotocol)