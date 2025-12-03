function useDeviceLocation() {
  if (!navigator.geolocation) { alert('Geolocation not supported'); return; }
  navigator.geolocation.getCurrentPosition(function(pos){
    document.getElementById('lat').value = pos.coords.latitude;
    document.getElementById('lng').value = pos.coords.longitude;
    if (typeof deviceMarker !== 'undefined' && deviceMarker) {
      deviceMarker.setLatLng([pos.coords.latitude, pos.coords.longitude]);
    }
  }, function(err){ alert('Unable to retrieve location: ' + err.message); }, { enableHighAccuracy:true });
}
