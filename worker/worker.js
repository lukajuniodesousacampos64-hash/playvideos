export default {
  async fetch(req, env) {
    const cors = {"Access-Control-Allow-Origin": env.ALLOWED_ORIGIN, "Access-Control-Allow-Headers": "content-type,x-app-key", "Access-Control-Allow-Methods": "POST,OPTIONS"};
    if (req.method === "OPTIONS") return new Response(null, {headers: cors});
    if (req.method !== "POST" || req.headers.get("x-app-key") !== env.APP_KEY) return new Response("não autorizado", {status: 401, headers: cors});
    const b = await req.json();
    const tema = String(b.tema || "").slice(0, 300), modelo = b.modelo === "3d" ? "3d" : "dinamico";
    const id = String(b.id || "").replace(/[^a-z0-9-]/gi, "").slice(0, 40);
    if (!tema || !id) return new Response("dados inválidos", {status: 400, headers: cors});
    const r = await fetch(`https://api.github.com/repos/${env.GH_REPO}/actions/workflows/gerar.yml/dispatches`, {
      method: "POST",
      headers: {Authorization: `Bearer ${env.GH_TOKEN}`, "User-Agent": "play-videos", Accept: "application/vnd.github+json"},
      body: JSON.stringify({ref: "main", inputs: {id, modelo, tema}})});
    return new Response(r.ok ? "ok" : "erro github " + r.status, {status: r.ok ? 200 : 502, headers: cors});
  }
};
