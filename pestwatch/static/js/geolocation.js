// geolocation.js — used on report page to use device location
function useDeviceLocation() {
    if (!navigator.geolocation) {
        alert('Geolocation not supported by your browser');
        return;
    }
    navigator.geolocation.getCurrentPosition(function(position) {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        document.getElementById('lat').value = lat;
        document.getElementById('lng').value = lng;
        if (typeof map !== 'undefined') {
            map.setView([lat, lng], 13);
            if (typeof deviceMarker !== 'undefined') {
                deviceMarker.setLatLng([lat, lng]);
            } else {
                deviceMarker = L.marker([lat, lng]).addTo(map);
            }
        }
    }, function(err){
        alert('Unable to retrieve location: ' + err.message);
    }, { enableHighAccuracy: true });
}
