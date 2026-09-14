window.GeoTriggerMap = {
  addTiles: function (map) {
    const key = (document.body.dataset.mapKey || "").trim();
    if (key.indexOf("pk.") === 0) {
      L.tileLayer(
        "https://api.mapbox.com/styles/v1/mapbox/dark-v11/tiles/256/{z}/{x}/{y}?access_token=" +
          encodeURIComponent(key),
        {
          attribution: "&copy; Mapbox &copy; OpenStreetMap",
          maxZoom: 19,
        },
      ).addTo(map);
      return;
    }
    if (key) {
      L.tileLayer(
        "https://api.maptiler.com/maps/dataviz-dark/256/{z}/{x}/{y}.png?key=" + encodeURIComponent(key),
        {
          attribution: "&copy; MapTiler &copy; OpenStreetMap",
          maxZoom: 19,
        },
      ).addTo(map);
      return;
    }
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
      maxZoom: 19,
    }).addTo(map);
  },
};
