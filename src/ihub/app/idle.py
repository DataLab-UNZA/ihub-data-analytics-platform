"""Pause idle browser sessions so the Cloud Run instance can scale to zero.

A Streamlit page keeps a live connection to the server while it is open, and
Cloud Run bills the instance for as long as any connection is open. After
``IDLE_MINUTES`` without mouse, keyboard, scroll or touch activity, the page
moves to a static "session paused" page (served from ``app/static``), which
closes the connection. See docs/DEPLOYMENT.md and ADR-002.

Every page should call ``pause_when_idle()`` straight after
``st.set_page_config``.
"""

from __future__ import annotations

import streamlit.components.v1 as components

IDLE_MINUTES = 20
PAUSED_PAGE = "app/static/paused.html"

# The component runs in a sandboxed iframe that may not navigate the page
# itself, so it adds a small script to the parent page (same origin), once.
_SCRIPT = """
<script>
(function () {{
  const doc = window.parent.document;
  if (doc.getElementById("ihub-idle")) return;
  const s = doc.createElement("script");
  s.id = "ihub-idle";
  s.textContent = `
    (function () {{
      const limit = {limit_ms};
      let last = Date.now();
      const reset = () => {{ last = Date.now(); }};
      ["mousemove", "mousedown", "keydown", "scroll", "touchstart", "wheel"]
        .forEach((e) => window.addEventListener(e, reset, {{ passive: true, capture: true }}));
      setInterval(() => {{
        if (Date.now() - last > limit) {{
          const back = encodeURIComponent(window.location.pathname + window.location.search);
          window.location.replace("/{paused}?return=" + back);
        }}
      }}, 30000);
    }})();
  `;
  doc.head.appendChild(s);
}})();
</script>
"""


def pause_when_idle(minutes: int = IDLE_MINUTES) -> None:
    """Install the idle-pause script on the current page (invisible)."""
    components.html(
        _SCRIPT.format(limit_ms=minutes * 60 * 1000, paused=PAUSED_PAGE),
        height=0,
    )
