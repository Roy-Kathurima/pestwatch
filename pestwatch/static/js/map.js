var map = L.map('map').setView([-1.28,36.82],6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

var marker;

function locate(){
navigator.geolocation.getCurrentPosition(function(pos){
let lat = pos.coords.latitude;
let lng = pos.coords.longitude;

document.getElementById("lat").value = lat;
document.getElementById("lng").value = lng;

if(marker) marker.setLatLng([lat,lng])
else marker = L.marker([lat,lng]).addTo(map)

map.setView([lat,lng],12)
});
}

map.on("click", function(e){
if(marker) marker.setLatLng(e.latlng)
else marker=L.marker(e.latlng).addTo(map)

document.getElementById("lat").value= e.latlng.lat
document.getElementById("lng").value= e.latlng.lng
})
