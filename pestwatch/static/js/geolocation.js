function getLocation(){
   navigator.geolocation.getCurrentPosition(pos=>{
     document.getElementById("lat").value = pos.coords.latitude;
     document.getElementById("lon").value = pos.coords.longitude;
   })
}
