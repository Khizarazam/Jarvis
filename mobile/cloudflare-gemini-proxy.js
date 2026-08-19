// Jarvis — free Gemini CORS proxy (Cloudflare Worker)
//
// Why this exists: Google's Gemini API does not support direct calls from
// browser JavaScript (no CORS headers), unlike Anthropic's Claude API.
// This tiny worker sits in between: the Jarvis app calls THIS worker (which
// does allow CORS), and the worker forwards the request to Gemini using a
// key that's stored securely as a Cloudflare secret — never shipped to the
// browser at all.
//
// Setup: paste this into a new Cloudflare Worker (dash.cloudflare.com →
// Workers & Pages → Create → Edit code), then add a secret named
// GEMINI_API_KEY under Settings → Variables and Secrets with your
// aistudio.google.com API key as the value. Deploy, then copy the worker's
// *.workers.dev URL into Jarvis's Settings → AI Assistant → API key field.

export default {
  async fetch(request, env) {
    // Handle the browser's CORS preflight check.
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type"
        }
      });
    }

    if (request.method !== "POST") {
      return new Response("Method not allowed — POST only.", { status: 405 });
    }

    if (!env.GEMINI_API_KEY) {
      return new Response(
        JSON.stringify({ error: { message: "GEMINI_API_KEY secret is not set on this worker." } }),
        { status: 500, headers: { "content-type": "application/json", "Access-Control-Allow-Origin": "*" } }
      );
    }

    let body;
    try {
      body = await request.json();
    } catch (e) {
      return new Response(
        JSON.stringify({ error: { message: "Invalid JSON body." } }),
        { status: 400, headers: { "content-type": "application/json", "Access-Control-Allow-Origin": "*" } }
      );
    }

    const model = body.model || "gemini-2.5-flash";
    const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${env.GEMINI_API_KEY}`;

    const upstream = await fetch(geminiUrl, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        contents: body.contents,
        systemInstruction: body.systemInstruction,
        generationConfig: body.generationConfig
      })
    });

    const data = await upstream.text();
    return new Response(data, {
      status: upstream.status,
      headers: {
        "content-type": "application/json",
        "Access-Control-Allow-Origin": "*"
      }
    });
  }
};
