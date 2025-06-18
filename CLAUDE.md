# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an HTML-based MCP (Model Context Protocol) client webapp that provides a web interface for interacting with AI models through OpenRouter. The entire application is contained in a single HTML file (`mcp-client-webapp.html`) that includes HTML, CSS, and JavaScript.

## Architecture

**Single-page application structure:**
- Complete self-contained web application in one HTML file
- No build process or external dependencies required
- Uses vanilla JavaScript with ES6 classes
- CSS custom properties for theming (light/dark mode support)
- Server-Sent Events (SSE) for MCP server communication

**Key components:**
- `MCPClient` class: Main application controller handling MCP protocol, OpenRouter API, and UI interactions
- MCP protocol implementation using JSON-RPC over SSE
- OpenRouter API integration for LLM communication
- File attachment support (images and PDFs)
- Context tracking with token estimation
- Tool execution with approval/auto-approval workflow

## Development

**Running the application:**
- Open `mcp-client-webapp.html` directly in a web browser
- No build process or server required for the client
- Requires an MCP server running on `http://localhost:8000/sse` by default

**File structure:**
- `mcp-client-webapp.html` - Complete application (HTML + CSS + JS)
- `README.md` - Basic project description
- No package.json, dependencies, or build configuration

## MCP Integration

The client implements the Model Context Protocol for tool execution:
- Connects to MCP servers via Server-Sent Events
- Supports tool discovery, execution, and result handling
- Implements proper JSON-RPC message handling
- Tool execution can be auto-approved or require manual confirmation

## API Integration

Uses OpenRouter API for LLM communication:
- Supports both free and premium models
- Handles model context limits with visual indicators
- Implements tool calling via OpenAI-compatible API
- File attachment support for images and PDFs

## Configuration

Settings are stored in localStorage:
- OpenRouter API key
- Selected model
- System prompt
- Auto-approve tools preference
- Dark mode preference