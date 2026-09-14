(function () {
  const mapEl = document.getElementById("editor-map");
  if (!mapEl || typeof L === "undefined") return;

  const latInput = document.querySelector('input[name="latitude"]');
  const lonInput = document.querySelector('input[name="longitude"]');
  const radiusInput = document.querySelector('input[name="radius_meters"]');

  const startLat = parseFloat(latInput.value) || 50.087;
  const startLon = parseFloat(lonInput.value) || 14.421;
  const startRadius = parseInt(radiusInput.value, 10) || 100;

  const map = L.map(mapEl).setView([startLat, startLon], latInput.value ? 16 : 12);
  GeoTriggerMap.addTiles(map);

  const marker = L.marker([startLat, startLon], { draggable: true }).addTo(map);
  const circle = L.circle([startLat, startLon], {
    radius: startRadius,
    color: "#c4d47a",
    weight: 1,
    fillColor: "#c4d47a",
    fillOpacity: 0.18,
  }).addTo(map);

  function syncFromMarker(latlng) {
    latInput.value = latlng.lat.toFixed(6);
    lonInput.value = latlng.lng.toFixed(6);
    circle.setLatLng(latlng);
  }

  function syncFromInputs() {
    const lat = parseFloat(latInput.value);
    const lon = parseFloat(lonInput.value);
    const radius = parseInt(radiusInput.value, 10);
    if (Number.isFinite(lat) && Number.isFinite(lon)) {
      const latlng = L.latLng(lat, lon);
      marker.setLatLng(latlng);
      circle.setLatLng(latlng);
    }
    if (Number.isFinite(radius) && radius > 0) {
      circle.setRadius(radius);
    }
  }

  marker.on("drag", function (event) {
    syncFromMarker(event.latlng);
  });
  map.on("click", function (event) {
    marker.setLatLng(event.latlng);
    syncFromMarker(event.latlng);
  });
  ["change", "input"].forEach(function (evt) {
    latInput.addEventListener(evt, syncFromInputs);
    lonInput.addEventListener(evt, syncFromInputs);
    radiusInput.addEventListener(evt, syncFromInputs);
  });
})();
