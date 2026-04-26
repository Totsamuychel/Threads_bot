/* ============================================================
   Threads Automation — Client-side JavaScript
   ============================================================ */

// API helper
async function api(url, method = 'GET', body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);
    const resp = await fetch(url, opts);
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || resp.statusText);
    }
    return resp.json();
}

// Formatting helpers
function formatTime(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleString('en-GB', {
        month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function percent(used, total) {
    if (!total || total === 0) return 0;
    return Math.min(100, Math.round((used || 0) / total * 100));
}

function getBarColor(used, total) {
    const p = percent(used, total);
    if (p > 85) return 'bar-red';
    if (p > 60) return 'bar-yellow';
    return 'bar-green';
}
