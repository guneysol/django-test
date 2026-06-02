/* BookNest progressive-enhancement scripts.
   Everything here is optional: forms and links work without JavaScript, and JS
   simply upgrades the experience (mobile menu, AJAX shelving, instant search,
   an interactive star picker, and the AI review summary). */

(function () {
  "use strict";

  // --- Mobile navigation toggle --------------------------------------------
  const toggle = document.querySelector(".nav-toggle");
  const links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      const open = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  // --- CSRF helper ----------------------------------------------------------
  function getCookie(name) {
    const match = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return match ? decodeURIComponent(match.pop()) : "";
  }

  // --- AJAX "add to reading list" toggle ------------------------------------
  const shelfBtn = document.querySelector("[data-shelf-url]");
  if (shelfBtn) {
    shelfBtn.addEventListener("click", function () {
      shelfBtn.disabled = true;
      fetch(shelfBtn.dataset.shelfUrl, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCookie("csrftoken"),
        },
      })
        .then(function (r) {
          if (!r.ok) throw new Error("Request failed");
          return r.json();
        })
        .then(function (data) {
          shelfBtn.textContent = data.shelved ? "✓ " + data.label : "＋ " + data.label;
          shelfBtn.setAttribute("aria-pressed", String(data.shelved));
          const counter = document.querySelector("[data-shelf-count]");
          if (counter) counter.textContent = data.count;
        })
        .catch(function () {
          shelfBtn.textContent = "Try again";
        })
        .finally(function () {
          shelfBtn.disabled = false;
        });
    });
  }

  // --- Instant search (search-as-you-type) ----------------------------------
  // Debounced fetch of just the results fragment, swapped in without a reload.
  const searchForm = document.querySelector("[data-live-search]");
  const resultsBox = document.querySelector("[data-results]");
  if (searchForm && resultsBox) {
    const input = searchForm.querySelector('input[type="search"]');
    const sort = searchForm.querySelector('select[name="sort"]');
    const spinner = searchForm.querySelector("[data-search-spinner]");
    let timer = null;
    let controller = null;

    function runSearch() {
      const params = new URLSearchParams(new FormData(searchForm));
      const qs = params.toString();
      if (controller) controller.abort();
      controller = new AbortController();
      if (spinner) spinner.classList.add("active");
      fetch(searchForm.dataset.resultsUrl + "?" + qs, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        signal: controller.signal,
      })
        .then(function (r) { return r.text(); })
        .then(function (html) {
          resultsBox.innerHTML = html;
          history.replaceState(null, "", qs ? "?" + qs : location.pathname);
        })
        .catch(function () { /* aborted or offline — ignore */ })
        .finally(function () { if (spinner) spinner.classList.remove("active"); });
    }

    if (input) {
      input.addEventListener("input", function () {
        clearTimeout(timer);
        timer = setTimeout(runSearch, 300);
      });
    }
    if (sort) sort.addEventListener("change", runSearch);
    searchForm.addEventListener("submit", function (e) {
      e.preventDefault();
      clearTimeout(timer);
      runSearch();
    });
  }

  // --- Interactive star rating picker ---------------------------------------
  // Upgrades the <select> on the review form into clickable stars.
  const ratingSelect = document.getElementById("id_rating");
  if (ratingSelect) {
    const widget = document.createElement("div");
    widget.className = "star-input";
    widget.setAttribute("role", "radiogroup");
    widget.setAttribute("aria-label", "Your rating");

    let current = parseInt(ratingSelect.value, 10) || 0;
    const buttons = [];
    for (let i = 1; i <= 5; i++) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "star-btn";
      b.textContent = "★";
      b.dataset.value = i;
      b.setAttribute("aria-label", i + (i > 1 ? " stars" : " star"));
      widget.appendChild(b);
      buttons.push(b);
    }
    function paint(n) {
      buttons.forEach(function (b, idx) { b.classList.toggle("on", idx < n); });
    }
    paint(current);
    widget.addEventListener("mouseover", function (e) {
      if (e.target.dataset.value) paint(+e.target.dataset.value);
    });
    widget.addEventListener("mouseleave", function () { paint(current); });
    widget.addEventListener("click", function (e) {
      if (!e.target.dataset.value) return;
      current = +e.target.dataset.value;
      ratingSelect.value = current;
      paint(current);
    });
    ratingSelect.style.display = "none";
    ratingSelect.parentNode.insertBefore(widget, ratingSelect);
  }

  // --- AI review summary ----------------------------------------------------
  const aiCard = document.querySelector("[data-ai-url]");
  if (aiCard) {
    const btn = aiCard.querySelector("[data-ai-btn]");
    const out = aiCard.querySelector("[data-ai-output]");

    function typeWriter(el, text) {
      el.textContent = "";
      let i = 0;
      (function step() {
        if (i <= text.length) {
          el.textContent = text.slice(0, i);
          i += 2;
          setTimeout(step, 12);
        }
      })();
    }

    if (btn && out) {
      btn.addEventListener("click", function () {
        const original = btn.textContent;
        btn.disabled = true;
        btn.textContent = "Analysing reviews…";
        out.hidden = false;
        out.classList.add("loading");
        out.textContent = "✨ Reading every review…";
        fetch(aiCard.dataset.aiUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            out.classList.remove("loading");
            typeWriter(out, data.summary);
          })
          .catch(function () {
            out.classList.remove("loading");
            out.textContent = "Could not generate a summary right now.";
          })
          .finally(function () {
            btn.disabled = false;
            btn.textContent = original;
          });
      });
    }
  }
})();
