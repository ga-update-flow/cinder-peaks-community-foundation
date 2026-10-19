// Progressive enhancement for navigation. All links work without JavaScript.
(function () {
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("primary-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  var items = document.querySelectorAll(".has-dropdown");
  function closeAll(except) {
    items.forEach(function (item) {
      if (item !== except) {
        item.classList.remove("is-open");
        var b = item.querySelector(".submenu-toggle");
        if (b) b.setAttribute("aria-expanded", "false");
      }
    });
  }
  items.forEach(function (item) {
    var btn = item.querySelector(".submenu-toggle");
    if (!btn) return;
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var open = !item.classList.contains("is-open");
      closeAll(item);
      item.classList.toggle("is-open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  });
  document.addEventListener("click", function (e) {
    if (!e.target.closest || !e.target.closest(".primary-nav")) {
      if (window.matchMedia("(min-width: 1101px)").matches) closeAll(null);
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      closeAll(null);
      if (nav && nav.classList.contains("is-open")) {
        nav.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.focus();
      }
    }
  });
})();
