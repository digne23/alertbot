/* AlertBot shared front-end helpers. */

const AlertBot = (() => {
  // ------------------------------------------------------------ requests
  async function api(path, options = {}) {
    const config = Object.assign({ headers: {} }, options);
    if (config.body && typeof config.body !== "string") {
      config.body = JSON.stringify(config.body);
      config.headers["Content-Type"] = "application/json";
    }

    const response = await fetch(path, config);
    if (response.status === 401) {
      throw new Error("Not authorised — reload and sign in again.");
    }
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const data = await response.json();
        detail = data.detail || detail;
      } catch (_) {
        /* not JSON */
      }
      throw new Error(detail);
    }
    if (response.status === 204) return null;
    return response.json();
  }

  // -------------------------------------------------------------- toasts
  function toast(message, kind = "") {
    let host = document.querySelector(".toast-host");
    if (!host) {
      host = document.createElement("div");
      host.className = "toast-host";
      document.body.appendChild(host);
    }
    const node = document.createElement("div");
    node.className = `toast ${kind}`;
    node.textContent = message;
    host.appendChild(node);
    setTimeout(() => node.remove(), 4200);
  }

  // --------------------------------------------------------------- utils
  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(
      /[&<>"']/g,
      (character) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[character],
    );
  }

  function timeAgo(iso) {
    if (!iso) return "—";
    const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (seconds < 60) return `${Math.max(0, seconds)}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ${minutes % 60}m ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  }

  function formatTime(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  function stateBadges(incident) {
    const badges = [];
    if (incident.state === "OPEN") {
      badges.push('<span class="badge open">open</span>');
    } else {
      badges.push('<span class="badge resolved">resolved</span>');
    }
    if (incident.acknowledged) badges.push('<span class="badge ack">acked</span>');
    if (incident.escalation_level > 0) {
      badges.push('<span class="badge escalated">escalated</span>');
    }
    if (incident.silenced) badges.push('<span class="badge silenced">silenced</span>');
    if (incident.source && incident.source !== "email") {
      badges.push(`<span class="badge muted">${escapeHtml(incident.source)}</span>`);
    }
    return badges.join(" ");
  }

  function copy(text) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(
        () => toast("Copied to clipboard", "ok"),
        () => toast("Could not copy", "err"),
      );
    }
  }

  // ------------------------------------------------------ live indicator
  function setLive(state, label) {
    const node = document.getElementById("live-indicator");
    if (!node) return;
    node.className = `live-dot ${state}`;
    node.innerHTML = `<i></i><span>${escapeHtml(label)}</span>`;
  }

  // ---------------------------------------------------- browser alerting
  // Best-effort desktop/Android web notification. The real alarm is the
  // phone push — this is only a courtesy for whoever has the tab open.
  const alerted = new Set();

  function askPermission() {
    if (!("Notification" in window)) {
      toast("This browser cannot show notifications", "err");
      return;
    }
    Notification.requestPermission().then((permission) => {
      toast(
        permission === "granted"
          ? "Browser notifications enabled"
          : "Browser notifications blocked",
        permission === "granted" ? "ok" : "err",
      );
    });
  }

  function browserNotify(incident) {
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    if (alerted.has(incident.id)) return;
    alerted.add(incident.id);
    try {
      const note = new Notification(`${incident.severity} — ${incident.service}`, {
        body: `${incident.provider}: ${incident.reason || "Incident opened"}`,
        tag: `alertbot-${incident.id}`,
        requireInteraction: true,
      });
      note.onclick = () => {
        window.focus();
        window.location.href = `/incident/${incident.id}`;
      };
    } catch (_) {
      /* Safari on iOS only allows this from a service worker */
    }
  }

  function seedAlerted(incidents) {
    incidents.forEach((incident) => alerted.add(incident.id));
  }

  // ------------------------------------------------------------- polling
  function every(seconds, fn) {
    fn();
    const id = setInterval(() => {
      if (document.visibilityState === "visible") fn();
    }, seconds * 1000);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") fn();
    });
    return id;
  }

  // ----------------------------------------------------------------- PWA
  function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        /* offline support is optional */
      });
    });
  }

  return {
    api,
    toast,
    escapeHtml,
    timeAgo,
    formatTime,
    stateBadges,
    copy,
    setLive,
    askPermission,
    browserNotify,
    seedAlerted,
    every,
    registerServiceWorker,
  };
})();

AlertBot.registerServiceWorker();
