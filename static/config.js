// NeXus Platform — Central API Configuration
// ─────────────────────────────────────────────────────────────────────────
// All HTML pages load this one file.
// When deploying to Render, replace YOUR_RENDER_URL with your actual URL.
// On localhost it auto-detects and uses local servers — no changes needed.
// ─────────────────────────────────────────────────────────────────────────

(function () {
    var isLocal = ['localhost', '127.0.0.1'].includes(window.location.hostname);

    window.NEXUS_CONFIG = {
        // ⚠ Replace YOUR_RENDER_URL with your Render deployment URL (keep https://)
        apiUrl: isLocal ? 'http://localhost:8000' : 'https://YOUR_RENDER_URL',
        wsUrl:  isLocal ? 'ws://localhost:8001'   : 'wss://YOUR_RENDER_URL',
    };
})();
