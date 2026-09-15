(function () {
  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function formatLocal(iso) {
    var date = new Date(iso);
    if (isNaN(date.getTime())) return null;
    return (
      date.getFullYear() +
      "-" +
      pad(date.getMonth() + 1) +
      "-" +
      pad(date.getDate()) +
      " " +
      pad(date.getHours()) +
      ":" +
      pad(date.getMinutes())
    );
  }

  document.querySelectorAll("time.local-time").forEach(function (el) {
    var text = formatLocal(el.getAttribute("datetime"));
    if (text) el.textContent = text;
  });
})();
