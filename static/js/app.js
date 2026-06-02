/* BookNest progressive-enhancement scripts.
   Everything here is optional: forms and links work without JavaScript, and JS
   simply upgrades the experience (mobile menu, AJAX shelving, live search). */

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
  // Posts to the shelf endpoint and updates the button in place, with no reload.
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
          shelfBtn.textContent = data.label;
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

  // --- Debounced live search ------------------------------------------------
  // Auto-submits the search form a short while after the user stops typing.
  const searchForm = document.querySelector("[data-live-search]");
  if (searchForm) {
    const input = searchForm.querySelector('input[type="search"]');
    let timer = null;
    if (input) {
      input.addEventListener("input", function () {
        clearTimeout(timer);
        timer = setTimeout(function () {
          searchForm.submit();
        }, 450);
      });
    }
  }
})();
