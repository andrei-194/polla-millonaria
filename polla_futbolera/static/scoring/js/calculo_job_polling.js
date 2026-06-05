(function () {
  var jobId = document.querySelector("[data-polling-job-id]");
  if (!jobId) return;

  var id = jobId.getAttribute("data-polling-job-id");
  var statusUrl = "/admin/scoring/calculojob/" + id + "/status/";

  function poll() {
    fetch(statusUrl)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.estado === "DONE" || data.estado === "ERROR") {
          location.reload();
        } else {
          setTimeout(poll, 2000);
        }
      })
      .catch(function () {
        setTimeout(poll, 5000);
      });
  }

  setTimeout(poll, 2000);
})();
