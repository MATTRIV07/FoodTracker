// Wires the "Scan now" button to an in-place recheck: POST /scan-now, then
// re-fetch "/" and swap in the refreshed deals list without a full page
// navigation. Falls back to a normal form submit if anything here throws.
(function () {
  const form = document.getElementById("scan-form");
  if (!form) return;

  const button = form.querySelector("button");
  const statusEl = document.getElementById("scan-status");

  function scoreByRestaurant(container) {
    const scores = {};
    container.querySelectorAll(".deal-card").forEach((card) => {
      const name = card.querySelector("h2");
      const score = card.querySelector(".score");
      if (name) scores[name.textContent.trim()] = score ? score.textContent.trim() : null;
    });
    return scores;
  }

  async function rescan() {
    button.disabled = true;
    const originalLabel = button.textContent;
    button.textContent = "Scanning…";
    if (statusEl) statusEl.textContent = "";

    try {
      await fetch(form.action, { method: "POST" });
      const resp = await fetch("/");
      const html = await resp.text();
      const doc = new DOMParser().parseFromString(html, "text/html");

      const oldDeals = document.querySelector(".deals");
      const newDeals = doc.querySelector(".deals");
      if (!oldDeals || !newDeals) {
        window.location.reload();
        return;
      }

      const before = scoreByRestaurant(oldDeals);
      oldDeals.replaceWith(newDeals);
      const after = scoreByRestaurant(newDeals);

      const changed = Object.keys(after).filter(
        (name) => after[name] !== null && after[name] !== before[name]
      );
      changed.forEach((name) => {
        const card = Array.from(newDeals.querySelectorAll(".deal-card")).find(
          (c) => c.querySelector("h2") && c.querySelector("h2").textContent.trim() === name
        );
        const scoreEl = card && card.querySelector(".score");
        if (scoreEl) {
          scoreEl.classList.add("score-flash");
          setTimeout(() => scoreEl.classList.remove("score-flash"), 1500);
        }
      });

      const todayEl = document.querySelector(".today");
      const newToday = doc.querySelector(".today");
      if (todayEl && newToday) todayEl.replaceWith(newToday);

      if (statusEl) {
        statusEl.textContent = changed.length
          ? `Score updated: ${changed.join(", ")}.`
          : "Rechecked — no score changes.";
      }
    } catch (err) {
      if (statusEl) statusEl.textContent = "Scan failed — try again.";
      console.error("Scan now failed:", err);
    } finally {
      button.disabled = false;
      button.textContent = originalLabel;
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    rescan();
  });
})();
