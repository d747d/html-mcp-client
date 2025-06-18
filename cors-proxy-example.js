#!/usr/bin/env node

/**
 * Simple CORS Proxy for MCP Client
 * 
 * This is a simple Node.js server that acts as a CORS proxy to allow
 * the HTML MCP client to connect to MCP servers running on different
 * ports or hosts.
 * 
 * Usage:
 *   node cors-proxy-example.js [port]
 * 
 * Then configure the MCP client to use:
 *   Connection Mode: Custom Proxy
 *   Custom Proxy URL: http://localhost:3001/proxy
 */

const http = require('http');
const https = require('https');
const { URL } = require('url');

const PORT = process.argv[2] || 3001;

const server = http.createServer((req, res) => {
    // Enable CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
    
    // Handle preflight requests
    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }
    
    // Health check
    if (req.url === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok', timestamp: new Date().toISOString() }));
        return;
    }
    
    // Proxy endpoint
    if (req.url.startsWith('/proxy')) {
        const urlParams = new URL(req.url, `http://localhost:${PORT}`);
        const targetUrl = urlParams.searchParams.get('url');
        
        if (!targetUrl) {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Missing url parameter' }));
            return;
        }
        
        try {
            const target = new URL(targetUrl);
            
            // Security: Only allow specific protocols
            if (!['http:', 'https:'].includes(target.protocol)) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Invalid protocol' }));
                return;
            }
            
            // Security: Block private networks in production
            const hostname = target.hostname.toLowerCase();
            const isPrivate = hostname === 'localhost' || 
                            hostname === '127.0.0.1' || 
                            hostname.startsWith('192.168.') ||
                            hostname.startsWith('10.') ||
                            hostname.startsWith('172.');
                            
            if (!isPrivate && process.env.NODE_ENV === 'production') {
                console.log(`Blocking private network access to ${hostname} in production`);
            }
            
            // Choose HTTP or HTTPS module
            const httpModule = target.protocol === 'https:' ? https : http;
            
            // Forward the request
            const proxyReq = httpModule.request(target, {
                method: req.method,
                headers: {
                    ...req.headers,
                    host: target.host,
                    // Remove origin to avoid CORS issues
                    origin: undefined,
                    referer: undefined
                }
            }, (proxyRes) => {
                // Forward status and headers
                res.writeHead(proxyRes.statusCode, proxyRes.headers);
                proxyRes.pipe(res);
            });
            
            proxyReq.on('error', (err) => {
                console.error('Proxy request error:', err.message);
                if (!res.headersSent) {
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Proxy request failed' }));
                }
            });
            
            // Forward request body
            req.pipe(proxyReq);
            
        } catch (err) {
            console.error('Invalid target URL:', err.message);
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Invalid target URL' }));
        }
    } else {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Not found' }));
    }
});

server.listen(PORT, () => {
    console.log(`CORS Proxy server running on http://localhost:${PORT}`);
    console.log(`Proxy endpoint: http://localhost:${PORT}/proxy?url=TARGET_URL`);
    console.log(`Health check: http://localhost:${PORT}/health`);
    console.log('');
    console.log('Configure your MCP client with:');
    console.log(`  Connection Mode: Custom Proxy`);
    console.log(`  Custom Proxy URL: http://localhost:${PORT}/proxy`);
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\nShutting down CORS proxy server...');
    server.close(() => {
        console.log('Server closed.');
        process.exit(0);
    });
});