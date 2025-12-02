// map.js — displays approved reports on the public map (index.html)
var map = L.map('map').setView([-1.286389, 36.817223], 6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Markers inserted from index.html template using server-side templating
