#!/usr/bin/env node

/**
 * MCP SSE Client Adapter with Iron Dome Authentication
 * 
 * Bridges stdio (standard MCP client input/output) to SSE (Server-Sent Events) MCP server.
 * 
 * SECURITY: This adapter includes the MCP_AUTH_TOKEN in all requests.
 * Only this authorized adapter can communicate with the MCP server.
 * Direct bypass attempts without the token will be rejected (403).
 * 
 * Usage: MCP_AUTH_TOKEN=xxx node mcp_client_adapter.js
 */

const EventSourceLib = require('eventsource');
const EventSource = EventSourceLib.EventSource || EventSourceLib;
const fetchLib = require('node-fetch');
const fetch = fetchLib.default || fetchLib;

const SSE_URL = process.env.MCP_SSE_URL || 'http://localhost:8000/sse';
const AUTH_TOKEN = process.env.MCP_AUTH_TOKEN;

// Validate token is provided
if (!AUTH_TOKEN) {
    console.error('[MCP Adapter] 🚫 ERROR: MCP_AUTH_TOKEN environment variable is required!');
    console.error('[MCP Adapter] This adapter cannot connect without authentication.');
    process.exit(1);
}

// Initial POST URL is unknown, will be provided by server via SSE 'endpoint' event
let postUrl = null;
let eventSource;
let messageQueue = []; // Buffer messages until we have a postUrl

// Connect to SSE endpoint with authentication
function connect() {
    console.error(`[MCP Adapter] 🔒 Connecting to ${SSE_URL} with Iron Dome authentication...`);

    // EventSource with custom headers for authentication
    eventSource = new EventSource(SSE_URL, {
        headers: {
            'X-MCP-Auth-Token': AUTH_TOKEN
        }
    });

    eventSource.onopen = () => {
        console.error('[MCP Adapter] ✅ Connected to SSE server (authenticated)');
    };

    // Handle endpoint event (contains the URL for POST requests)
    eventSource.addEventListener('endpoint', (event) => {
        const endpointPath = event.data.trim();

        // Simple resolution logic
        if (endpointPath.startsWith('http')) {
            postUrl = endpointPath;
        } else {
            // Construct absolute URL assuming standard structure
            const baseUrl = new URL(SSE_URL);
            postUrl = `${baseUrl.protocol}//${baseUrl.host}${endpointPath}`;
        }

        console.error(`[MCP Adapter] 📍 Received endpoint: ${postUrl}`);
        // Increased delay to ensure server-side mcp.run is ready
        setTimeout(() => flushQueue(), 2000);
    });

    eventSource.onmessage = (event) => {
        // Relay server messages to stdout (to MCP client)
        process.stdout.write(event.data + '\n');
    };

    eventSource.onerror = (error) => {
        console.error('[MCP Adapter] ❌ SSE Error:', error);
        // Check if it's an auth error
        if (error.status === 403) {
            console.error('[MCP Adapter] 🚫 Authentication failed! Check MCP_AUTH_TOKEN.');
            process.exit(1);
        }
    };
}

async function sendPost(message) {
    if (!postUrl) {
        messageQueue.push(message);
        return;
    }

    try {
        const response = await fetch(postUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-MCP-Auth-Token': AUTH_TOKEN  // Iron Dome: Include token in all requests
            },
            body: JSON.stringify(message)
        });

        if (!response.ok) {
            console.error(`[MCP Adapter] POST Error: ${response.status} ${response.statusText}`);
            const text = await response.text();
            console.error(`[MCP Adapter] Response: ${text}`);

            if (response.status === 403) {
                console.error('[MCP Adapter] 🚫 Iron Dome rejected request. Token may be invalid.');
            }
        }
    } catch (error) {
        console.error('[MCP Adapter] Failed to relay message:', error);
    }
}

function flushQueue() {
    while (messageQueue.length > 0 && postUrl) {
        const msg = messageQueue.shift();
        sendPost(msg);
    }
}

// Listen for client messages on stdin
process.stdin.setEncoding('utf8');
process.stdin.on('data', async (data) => {
    const lines = data.trim().split('\n');
    for (const line of lines) {
        if (!line.trim()) continue;
        try {
            const message = JSON.parse(line);
            sendPost(message);
        } catch (error) {
            console.error('[MCP Adapter] Failed to parse JSON:', error);
        }
    }
});

process.stdin.on('end', () => {
    console.error('[MCP Adapter] Client disconnected');
    if (eventSource) eventSource.close();
    process.exit(0);
});

// Start connection
connect();
