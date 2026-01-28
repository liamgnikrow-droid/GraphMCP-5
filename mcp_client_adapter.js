#!/usr/bin/env node

/**
 * MCP SSE Client Adapter
 * Bridges stdio (standard MCP client input/output) to SSE (Server-Sent Events) MCP server.
 * Usage: node mcp_client_adapter.js
 * The adapter connects to http://localhost:8000/sse and relays messages.
 */

const EventSourceLib = require('eventsource');
const EventSource = EventSourceLib.EventSource || EventSourceLib;
const fetchLib = require('node-fetch');
const fetch = fetchLib.default || fetchLib;

const SSE_URL = process.env.MCP_SSE_URL || 'http://localhost:8000/sse';
// Initial POST URL is unknown, will be provided by server via SSE 'endpoint' event
let postUrl = null;

let eventSource;
let messageQueue = []; // Buffer messages until we have a postUrl

// Connect to SSE endpoint
function connect() {
    console.error(`[MCP Adapter] Connecting to ${SSE_URL}...`);

    eventSource = new EventSource(SSE_URL);

    eventSource.onopen = () => {
        console.error('[MCP Adapter] Connected to SSE server');
    };

    // Handle endpoint event (contains the URL for POST requests)
    eventSource.addEventListener('endpoint', (event) => {
        // The event data is the relative or absolute URL. 
        // If relative, we need to resolve it against SSE_URL base.
        const endpointPath = event.data.trim();

        // Simple resolution logic
        if (endpointPath.startsWith('http')) {
            postUrl = endpointPath;
        } else {
            // Construct absolute URL assuming standard structure
            const baseUrl = new URL(SSE_URL);
            postUrl = `${baseUrl.protocol}//${baseUrl.host}${endpointPath}`;
        }

        console.error(`[MCP Adapter] Received endpoint: ${postUrl}`);
        // Increased delay to ensure server-side mcp.run is ready
        setTimeout(() => flushQueue(), 2000);
    });

    eventSource.onmessage = (event) => {
        // Relay server messages to stdout (to MCP client)
        process.stdout.write(event.data + '\n');
    };

    eventSource.onerror = (error) => {
        console.error('[MCP Adapter] SSE Error:', error);
        // Don't close immediately on error, EventSource retries automatically often.
        // But if closed, we might need to reconnect logic.
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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(message)
        });

        if (!response.ok) {
            console.error(`[MCP Adapter] POST Error: ${response.status} ${response.statusText}`);
            const text = await response.text();
            console.error(`[MCP Adapter] Response: ${text}`);
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
