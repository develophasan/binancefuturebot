/**
 * Cloudflare Worker - Binance API Proxy
 * Bu worker Binance API'sine erişimi proxy eder
 * Ücretsiz tier: 100,000 request/day
 */

export default {
  async fetch(request, env, ctx) {
    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-MBX-APIKEY',
    };

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: corsHeaders
      });
    }

    try {
      const url = new URL(request.url);
      
      // Binance base URLs
      const binanceTestnetBase = 'https://testnet.binance.vision';
      const binanceMainnetBase = 'https://api.binance.com';
      
      // Determine target (testnet or mainnet based on path)
      let targetBase = binanceTestnetBase;
      if (url.pathname.startsWith('/mainnet/')) {
        targetBase = binanceMainnetBase;
        url.pathname = url.pathname.replace('/mainnet', '');
      } else if (url.pathname.startsWith('/testnet/')) {
        url.pathname = url.pathname.replace('/testnet', '');
      }
      
      // Build target URL
      const targetUrl = targetBase + url.pathname + url.search;
      
      // Forward headers (especially API key)
      const headers = new Headers();
      for (const [key, value] of request.headers.entries()) {
        if (key.toLowerCase() !== 'host') {
          headers.set(key, value);
        }
      }
      
      // Make request to Binance
      const binanceResponse = await fetch(targetUrl, {
        method: request.method,
        headers: headers,
        body: request.method !== 'GET' && request.method !== 'HEAD' 
          ? await request.text() 
          : undefined,
      });
      
      // Get response
      const responseBody = await binanceResponse.text();
      
      // Return with CORS headers
      return new Response(responseBody, {
        status: binanceResponse.status,
        statusText: binanceResponse.statusText,
        headers: {
          ...corsHeaders,
          'Content-Type': binanceResponse.headers.get('Content-Type') || 'application/json',
        }
      });
      
    } catch (error) {
      return new Response(JSON.stringify({ 
        error: error.message,
        message: 'Proxy error'
      }), {
        status: 500,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json'
        }
      });
    }
  },
};
