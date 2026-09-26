(() => {
  const healthStatus = document.getElementById("healthStatus");
  const form = document.getElementById("recForm");
  const results = document.getElementById("results");
  const formNote = document.getElementById("formNote");
  const submitBtn = document.getElementById("submitBtn");
  const possDate = document.getElementById("possDate");
  const possBtn = document.getElementById("possBtn");
  const possOut = document.getElementById("possOut");
  const calOut = document.getElementById("calOut");

  function money(n) {
    return `$${Number(n).toFixed(2)}`;
  }

  async function loadHealth() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      if (data.ok) {
        healthStatus.textContent = `${data.rows} trips loaded · ${data.csv}`;
        healthStatus.className = "status ok";
      } else {
        healthStatus.textContent = data.error || "CSV missing";
        healthStatus.className = "status bad";
      }
    } catch {
      healthStatus.textContent = "Server not reachable";
      healthStatus.className = "status bad";
    }
  }

  async function loadCalibration() {
    try {
      const res = await fetch("/api/calibration");
      if (!res.ok) throw new Error("no cal");
      const data = await res.json();
      if (!data.sample_count) {
        calOut.textContent = "Not calibrated yet";
        return;
      }
      calOut.textContent = `MAPE ${data.mape_pct}% · factor ${data.global_factor}`;
    } catch {
      calOut.textContent = "Unavailable";
    }
  }

  const LOADING_MARK = `
    <span class="loading-mark" aria-hidden="true">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 28" width="120" height="28">
        <rect x="0" y="10" width="120" height="10" rx="5" fill="#1f262e"/>
        <g class="lane">
          <rect x="8" y="13.5" width="14" height="3" rx="1.5" fill="#e6a817"/>
          <rect x="30" y="13.5" width="14" height="3" rx="1.5" fill="#e6a817"/>
          <rect x="52" y="13.5" width="14" height="3" rx="1.5" fill="#e6a817"/>
          <rect x="74" y="13.5" width="14" height="3" rx="1.5" fill="#e6a817"/>
          <rect x="96" y="13.5" width="14" height="3" rx="1.5" fill="#e6a817"/>
          <rect x="118" y="13.5" width="14" height="3" rx="1.5" fill="#e6a817"/>
        </g>
        <g class="car">
          <rect x="42" y="4" width="28" height="12" rx="3" fill="#e8f0f2"/>
          <path d="M48 4 L54 0 H62 L68 4 Z" fill="#7eb8c9"/>
          <circle cx="48" cy="16" r="3.2" fill="#e6a817"/>
          <circle cx="64" cy="16" r="3.2" fill="#e6a817"/>
        </g>
      </svg>
    </span>`;

  function setFormNote(html, { loading = false, error = false } = {}) {
    formNote.hidden = false;
    formNote.classList.toggle("is-loading", loading);
    formNote.classList.toggle("is-error", error);
    formNote.innerHTML = html;
  }

  function setFormNoteLoading(message = "Finding better trip costs…") {
    setFormNote(
      `${LOADING_MARK}<span class="loading-copy">${escapeHtml(message)}</span>`,
      { loading: true }
    );
  }

  function setFormNoteText(text, { error = false } = {}) {
    setFormNote(`<span class="loading-copy">${escapeHtml(text)}</span>`, { error });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    submitBtn.disabled = true;
    setFormNoteLoading();
    results.innerHTML = "";

    const body = {
      distance_km: Number(document.getElementById("distance").value),
      duration_hours: Number(document.getElementById("duration").value),
      is_weekend: document.getElementById("weekend").checked,
      region: document.getElementById("region").value,
      use_ml: true,
      top_n: 8,
    };

    try {
      const res = await fetch("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Request failed");

      setFormNoteText(`${data.recommendations.length} options · ${data.rows_used} rows`);
      data.recommendations.forEach((rec, i) => {
        const li = document.createElement("li");
        li.style.animationDelay = `${i * 0.04}s`;
        li.innerHTML = `
          <span class="rank">${i + 1}</span>
          <span class="who">${escapeHtml(rec.provider || "?")} · ${escapeHtml(rec.model || "")}</span>
          <span class="cost">${money(rec.total_cost)}</span>
          <span class="meta">${escapeHtml(rec.method || "")}${
            rec.rate_floor_applied
              ? ` · floored from $${Number(rec.raw_total_cost).toFixed(2)}`
              : rec.calibration_factor != null
              ? ` · cal ×${Number(rec.calibration_factor).toFixed(2)}`
              : ""
          }</span>
        `;
        results.appendChild(li);
      });
    } catch (err) {
      setFormNoteText(String(err.message || err), { error: true });
    } finally {
      submitBtn.disabled = false;
    }
  });

  possBtn.addEventListener("click", async () => {
    const date = possDate.value;
    if (!date) {
      possOut.textContent = "Pick a date";
      return;
    }
    possOut.textContent = "…";
    try {
      const q = new URLSearchParams({ date, distance_km: "40", duration_hours: "1" });
      const res = await fetch(`/api/possibility?${q}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed");
      possOut.textContent = `${Number(data.possibility_pct).toFixed(0)}% · ${data.method || ""}`;
    } catch (err) {
      possOut.textContent = String(err.message || err);
    }
  });

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  possDate.value = tomorrow.toISOString().slice(0, 10);

  loadHealth();
  loadCalibration();
})();
