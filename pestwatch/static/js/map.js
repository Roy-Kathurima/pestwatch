function loadMap(reports) {
  var map = L.map("map").setView([-1.28, 36.82], 6);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);

  reports.forEach(r => {
    L.marker([r.lat, r.lng]).addTo(map)
      .bindPopup(r.title);
  });
}
