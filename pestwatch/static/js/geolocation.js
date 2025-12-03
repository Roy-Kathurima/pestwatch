function useDeviceLocation() {
  if (!navigator.geolocation) { alert("Geolocation not supported by browser"); return; }
  navigator.geolocation.getCurrentPosition(function(pos){
    var lat = pos.coords.latitude;
    var lng = pos.coords.longitude;
    var latEl = document.getElementById("lat");
    var lngEl = document.getElementById("lng");
    if (latEl) latEl.value = lat;
    if (lngEl) lngEl.value = lng;
    alert("Device location added to the form.");
  }, function(err){
    alert("Unable to retrieve location: " + err.message);
  }, { enableHighAccuracy: true });
}
