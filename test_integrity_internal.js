const EventSource = require('eventsource');
const http = require('http');

// USE INTERNAL SERVICE NAME
const SSE_URL = 'http://graphmcp-core:8000/sse';
const TOKEN = 'b7d1aa6b7ee609152a8bbe94813beab1446028e759c4dcdae3b16f6360e231eb';

let postUrl = null;
let pendingRequests = new Map(); // id -> {resolve, reject}

function httpPost(url, data) {
    const json = JSON.stringify(data);
    const u = new URL(url);
    const options = {
        hostname: u.hostname,
        port: u.port,
        path: u.pathname + u.search,
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(json),
            'X-MCP-Auth-Token': TOKEN
        }
    };
    return new Promise((resolve, reject) => {
        const req = http.request(options, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => resolve(body));
        });
        req.on('error', reject);
        req.write(json);
        req.end();
    });
}

function callTool(name, args, id) {
    return new Promise((resolve, reject) => {
        pendingRequests.set(id, { resolve, reject });
        console.log(`📤 Sending ${name}...`);

        httpPost(postUrl, {
            jsonrpc: '2.0',
            id: id,
            method: 'tools/call',
            params: { name: name, arguments: args }
        }).catch(err => {
            pendingRequests.delete(id);
            reject(err);
        });
    });
}

async function testTools() {
    console.log('🔍 Testing Agent Capabilities (INTERNAL Async)...');

    return new Promise((resolve, reject) => {
        const es = new EventSource(SSE_URL, { headers: { 'X-MCP-Auth-Token': TOKEN } });

        es.onmessage = async (e) => {
            try {
                const msg = JSON.parse(e.data);

                // Handle Pending Requests (Responses)
                if (msg.id && pendingRequests.has(msg.id)) {
                    const { resolve, reject } = pendingRequests.get(msg.id);
                    pendingRequests.delete(msg.id);
                    if (msg.error) reject(msg.error);
                    else resolve(msg.result);
                    return;
                }

                if (msg.id === 'init') {
                    console.log('✅ SSE Connected.');
                    // Send notification initialized
                    await httpPost(postUrl, { jsonrpc: '2.0', method: 'notifications/initialized', params: {} });

                    try {
                        // TEST 1: Look Around
                        console.log('🧪 Testing look_around...');
                        const res1 = await callTool('look_around', {}, 'req-1');
                        console.log('✅ Look Around: SUCCESS');

                        // TEST 2: Refresh Knowledge
                        console.log('🧪 Testing refresh_knowledge...');
                        const res2 = await callTool('refresh_knowledge', {}, 'req-2');
                        console.log('✅ Refresh Knowledge: SUCCESS');
                        console.log('   Output:', res2.content[0].text);

                        // TEST 3: Get Full Context
                        console.log('🧪 Testing get_full_context...');
                        const res3 = await callTool('get_full_context', { query: 'авторизация' }, 'req-3');
                        console.log('✅ Get Full Context: SUCCESS');

                        es.close();
                        resolve();

                    } catch (err) {
                        console.error('❌ TEST FAILED:', err);
                        es.close();
                        // Don't reject main promise to visualize output, just exit
                        process.exit(1);
                    }
                }
            } catch (err) { console.error(err); }
        };

        es.addEventListener('endpoint', (e) => {
            const p = e.data.trim();
            if (p.startsWith('http')) {
                postUrl = p;
            } else {
                const baseUrl = new URL(SSE_URL);
                postUrl = `${baseUrl.protocol}//${baseUrl.host}${p}`;
            }
            // Send Init
            httpPost(postUrl, {
                jsonrpc: '2.0', id: 'init', method: 'initialize',
                params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'test-internal', version: '1' } }
            });
        });

        es.onerror = (err) => {
            console.error("Connection Error:", err);
            reject(err);
        };
    });
}

testTools();
