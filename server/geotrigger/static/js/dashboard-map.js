(function () {
  const el = document.getElementById("map");
  if (!el || typeof L === "undefined") return;

  const locations = JSON.parse(el.dataset.locations || "[]");
  const map = L.map(el, { scrollWheelZoom: true });
  GeoTriggerMap.addTiles(map);

  const bounds = [];
  locations.forEach(function (loc) {
    const latlng = [loc.latitude, loc.longitude];
    bounds.push(latlng);
    L.circle(latlng, {
      radius: loc.radius_meters,
      color: "#c4d47a",
      weight: 1,
      fillColor: "#c4d47a",
      fillOpacity: 0.15,
    }).addTo(map);
    L.circleMarker(latlng, {
      radius: 5,
      color: "#c4d47a",
      fillColor: "#c4d47a",
      fillOpacity: 1,
    }).addTo(map).bindPopup(loc.name + " · " + loc.radius_meters + " m");
  });

  if (bounds.length === 1) {
    map.setView(bounds[0], 15);
  } else if (bounds.length > 1) {
    map.fitBounds(bounds, { padding: [32, 32] });
  } else {
    map.setView([50.08, 14.43], 11);
  }
})();
