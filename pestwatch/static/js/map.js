function loadMap(reports) {
  try {
    var el = document.getElementById("map");
    if (!el) return;
    var map = L.map("map").setView([-1.286389, 36.817223], 6);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);
    if (!Array.isArray(reports)) return;
    reports.forEach(r => {
      if (r.lat && r.lng) {
        var marker = L.marker([r.lat, r.lng]).addTo(map);
        var html = `<strong>${r.title || "Report"}</strong><br>${r.details ? r.details.substring(0,120) + "..." : ""}`;
        marker.bindPopup(html);
      }
    });
  } catch(e) { console.error("map error", e); }
}
