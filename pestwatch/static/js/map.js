function renderMap(elementId, points) {
  if (!document.getElementById(elementId)) return;
  var map = L.map(elementId).setView([-1.286389, 36.817223], 6);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);
  if (!points || !points.length) return;
  var bounds = [];
  points.forEach(p => {
    if (p.lat && p.lng) {
      var marker = L.marker([p.lat, p.lng]).addTo(map);
      var popup = `<strong>${p.title || "Report"}</strong><br>${p.details || ""}`;
      if (p.image) popup += `<br><img src="/uploads/${p.image}" style="max-width:180px;margin-top:6px;display:block;">`;
      marker.bindPopup(popup);
      bounds.push([p.lat, p.lng]);
    }
  });
  if (bounds.length) map.fitBounds(bounds, { padding: [40,40] });
}
