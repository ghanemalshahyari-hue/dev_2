'use strict';
/*
 * Enterprise Dashboard — app.js v2.0
 * All offline — no external scripts.
 * ================================================================ */

// ─── Clock ─────────────────────────────────────────────────────────
(function initClock() {
    const el = document.getElementById('currentTime');
    if (!el) return;

    function tick() {
        const now = new Date();
        el.textContent = now.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
    }
    tick();
    setInterval(tick, 60_000);
})();


// ─── CEO Circular Dashboard ────────────────────────────────────────
(function initCEODashboard() {
    const charts = document.querySelectorAll('.dept-chart');
    if (!charts.length) return;

    /**
     * Render a dual-ring doughnut chart on a canvas.
     * Outer ring = competence %, inner ring = completion %.
     */
    function renderDeptChart(canvas) {
        const competence = parseFloat(canvas.dataset.competence) || 0;
        const completion = parseFloat(canvas.dataset.completion) || 0;
        const color = canvas.dataset.color || '#4F8EF7';

        new Chart(canvas, {
            type: 'doughnut',
            data: {
                datasets: [
                    {
                        // Outer ring — competence
                        data: [competence, 100 - competence],
                        backgroundColor: [color, 'rgba(255,255,255,0.06)'],
                        borderWidth: 0,
                        weight: 1.4,
                    },
                    {
                        // Inner ring — completion
                        data: [completion, 100 - completion],
                        backgroundColor: ['#34D399', 'rgba(255,255,255,0.04)'],
                        borderWidth: 0,
                        weight: 1,
                    },
                ],
            },
            options: {
                cutout: '55%',
                responsive: true,
                maintainAspectRatio: true,
                animation: { duration: 800, easing: 'easeOutQuart' },
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
            },
        });
    }

    charts.forEach(renderDeptChart);

    // ── Department detail modal population ──
    const detailModal = document.getElementById('deptDetailModal');
    if (detailModal) {
        detailModal.addEventListener('show.bs.modal', function (e) {
            const card = e.relatedTarget;
            const comp = parseFloat(card.dataset.competence) || 0;
            const done = parseFloat(card.dataset.completion) || 0;
            const name = card.dataset.deptName || '—';
            const desc = card.dataset.deptDesc || '—';
            const person = card.dataset.deptPerson || '—';

            document.getElementById('modalDeptName').textContent = name;
            document.getElementById('modalCompetence').textContent = comp.toFixed(1) + '%';
            document.getElementById('modalCompletion').textContent = done.toFixed(1) + '%';
            document.getElementById('modalCompetenceBar').style.width = comp + '%';
            document.getElementById('modalCompletionBar').style.width = done + '%';
            document.getElementById('modalDescription').textContent = desc;
            document.getElementById('modalPerson').textContent = person;
        });
    }

    // ── Auto-poll metrics every 60s ──
    const API_URL = '/api/dashboard/overview';
    let refreshIcon = document.getElementById('refreshIcon');

    function updateDashboard(data) {
        // Update company averages
        const avgComp = document.getElementById('avgCompetence');
        const avgDone = document.getElementById('avgCompletion');
        const lastUpd = document.getElementById('lastUpdate');

        if (avgComp) avgComp.textContent = (data.averages.competence || 0).toFixed(1) + '%';
        if (avgDone) avgDone.textContent = (data.averages.completion || 0).toFixed(1) + '%';
        if (lastUpd) {
            const d = new Date(data.updated_at);
            lastUpd.textContent = d.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
        }
    }

    async function pollMetrics() {
        // Spinning indicator
        if (refreshIcon) refreshIcon.classList.add('spin');
        try {
            const res = await fetch(API_URL, { credentials: 'same-origin' });
            if (res.ok) {
                const data = await res.json();
                updateDashboard(data);
            }
        } catch (_) { /* silent fail — server might be briefly busy */ }
        finally {
            if (refreshIcon) refreshIcon.classList.remove('spin');
        }
    }

    // Poll every 60 seconds
    setInterval(pollMetrics, 60_000);
})();


// ─── Pending badge (navbar) ────────────────────────────────────────
(function initPendingBadge() {
    const badge = document.getElementById('pendingBadge');
    if (!badge) return;

    async function checkPending() {
        try {
            const res = await fetch('/api/access/pending-count', { credentials: 'same-origin' });
            if (res.ok) {
                const data = await res.json();
                if (data.pending > 0) {
                    badge.textContent = data.pending;
                    badge.style.display = '';
                } else {
                    badge.style.display = 'none';
                }
            }
        } catch (_) { }
    }

    checkPending();
    setInterval(checkPending, 30_000);
})();


// ─── Spin animation for refresh icon ──────────────────────────────
(function addSpinCSS() {
    const style = document.createElement('style');
    style.textContent = `
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    .spin { animation: spin 0.8s linear infinite; }
  `;
    document.head.appendChild(style);
})();


// ─── Auto-dismiss flash alerts ─────────────────────────────────────
(function autoDismissAlerts() {
    setTimeout(function () {
        document.querySelectorAll('.flash-container .alert').forEach(function (el) {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
            if (bsAlert) bsAlert.close();
        });
    }, 6_000);
})();
