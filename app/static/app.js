// Frontend application logic for Geospatial File Measurement API

let map = null;
let geojsonLayer = null;
let currentMeasurementsData = null;

document.addEventListener("DOMContentLoaded", () => {
  initMap();
  setupUploadHandlers();
  setupSampleButton();
});

function initMap() {
  map = L.map("map").setView([20, 0], 2);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap contributors",
  }).addTo(map);
}

function setupUploadHandlers() {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const btnUpload = document.getElementById("btn-upload");
  const selectedName = document.getElementById("selected-file-name");

  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("border-indigo-500", "bg-indigo-50/60");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("border-indigo-500", "bg-indigo-50/60");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("border-indigo-500", "bg-indigo-50/60");
    if (e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      handleFileSelected(fileInput.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      handleFileSelected(fileInput.files[0]);
    }
  });

  btnUpload.addEventListener("click", () => {
    if (fileInput.files.length > 0) {
      uploadAndProcessFile(fileInput.files[0]);
    }
  });

  document.getElementById("btn-copy-json").addEventListener("click", () => {
    if (currentMeasurementsData) {
      navigator.clipboard.writeText(JSON.stringify(currentMeasurementsData, null, 2));
      alert("Measurements JSON copied to clipboard!");
    }
  });
}

function handleFileSelected(file) {
  const selectedName = document.getElementById("selected-file-name");
  const btnUpload = document.getElementById("btn-upload");
  selectedName.querySelector("span").textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  selectedName.classList.remove("hidden");
  btnUpload.disabled = false;
}

async function uploadAndProcessFile(file) {
  showStatus("Processing file and calculating geometric measurements...", "info");
  const btnUpload = document.getElementById("btn-upload");
  btnUpload.disabled = true;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const uploadRes = await fetch("/api/files/", {
      method: "POST",
      body: formData,
    });

    if (!uploadRes.ok) {
      const err = await uploadRes.json();
      throw new Error(err.message || err.detail || "Upload failed");
    }

    const fileInfo = await uploadRes.json();

    // Fetch full measurements
    const measRes = await fetch(`/api/files/${fileInfo.id}/measurements/`);
    if (!measRes.ok) {
      throw new Error("Failed to retrieve measurements.");
    }

    const measurementsData = await measRes.json();
    currentMeasurementsData = measurementsData;

    renderResults(fileInfo, measurementsData);
    showStatus("File successfully processed and measurements calculated!", "success");
  } catch (err) {
    showStatus(`Error: ${err.message}`, "error");
  } finally {
    btnUpload.disabled = false;
  }
}

function renderResults(info, data) {
  document.getElementById("results-section").classList.remove("hidden");

  // Summary cards
  document.getElementById("card-status").textContent = info.status;
  document.getElementById("card-crs").textContent = info.crs;
  document.getElementById("card-filename").textContent = info.filename;
  document.getElementById("card-id").textContent = `ID: ${info.id}`;

  const sum = data.summary;
  document.getElementById("card-total-area").textContent = `${formatNum(sum.total_area_sq_meters)} m²`;
  document.getElementById("card-area-sub").textContent = `${sum.total_area_sq_km.toFixed(4)} km² • ${sum.total_area_hectares.toFixed(2)} ha`;

  document.getElementById("card-total-length").textContent = `${formatNum(sum.total_length_meters)} m`;
  document.getElementById("card-length-sub").textContent = `${sum.total_length_km.toFixed(4)} km`;

  document.getElementById("card-total-features").textContent = sum.total_features;
  document.getElementById("badge-poly").textContent = `${sum.polygon_count} Poly`;
  document.getElementById("badge-line").textContent = `${sum.linestring_count} Lines`;
  document.getElementById("badge-point").textContent = `${sum.point_count} Points`;

  // Links and Preview
  const infoUrl = `/api/files/${info.id}/`;
  const measUrl = `/api/files/${info.id}/measurements/`;
  document.getElementById("link-file-info").textContent = `GET ${infoUrl}`;
  document.getElementById("btn-view-info").href = infoUrl;
  document.getElementById("link-file-measurements").textContent = `GET ${measUrl}`;
  document.getElementById("btn-view-measurements").href = measUrl;

  document.getElementById("json-preview").textContent = JSON.stringify(data, null, 2);

  // Render Map
  renderGeoJSONOnMap(data.features);

  // Render Table
  renderTable(data.features);
}

function renderGeoJSONOnMap(features) {
  if (geojsonLayer) {
    map.removeLayer(geojsonLayer);
  }

  const geojsonFeatures = features.map((f) => ({
    type: "Feature",
    properties: {
      id: f.feature_id,
      type: f.geometry_type,
      measurements: f.measurements,
      ...f.properties,
    },
    geometry: f.geometry,
  }));

  const featureCollection = {
    type: "FeatureCollection",
    features: geojsonFeatures,
  };

  geojsonLayer = L.geoJSON(featureCollection, {
    style: (feature) => {
      const type = feature.geometry.type;
      if (type.includes("Polygon")) {
        return { color: "#4f46e5", fillColor: "#818cf8", fillOpacity: 0.45, weight: 2 };
      } else if (type.includes("Line")) {
        return { color: "#0284c7", weight: 4 };
      }
      return { color: "#d97706", weight: 2 };
    },
    onEachFeature: (feature, layer) => {
      const m = feature.properties.measurements;
      let popupContent = `<div class="font-sans text-xs">
        <strong class="text-indigo-800 text-sm">Feature: ${feature.properties.id}</strong><br/>
        <span class="text-slate-500 font-semibold">Type:</span> ${feature.properties.type}<br/>`;

      if (m && m.area_sq_meters != null) {
        popupContent += `<span class="text-slate-500 font-semibold">Area:</span> <b>${formatNum(m.area_sq_meters)} m²</b> (${m.area_hectares} ha)<br/>`;
        if (m.perimeter_meters != null) {
          popupContent += `<span class="text-slate-500 font-semibold">Perimeter:</span> ${formatNum(m.perimeter_meters)} m<br/>`;
        }
      }
      if (m && m.length_meters != null) {
        popupContent += `<span class="text-slate-500 font-semibold">Length:</span> <b>${formatNum(m.length_meters)} m</b> (${m.length_km} km)<br/>`;
      }
      if (m && m.projected_crs) {
        popupContent += `<span class="text-slate-400">Projection:</span> ${m.projected_crs}<br/>`;
      }
      popupContent += `</div>`;
      layer.bindPopup(popupContent);
    },
  }).addTo(map);

  try {
    const bounds = geojsonLayer.getBounds();
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [30, 30] });
    }
  } catch (e) {
    console.error("Could not fit bounds:", e);
  }
}

function renderTable(features) {
  const tbody = document.getElementById("features-table-body");
  tbody.innerHTML = "";

  features.forEach((f) => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50 transition border-b border-slate-100";

    const m = f.measurements || {};
    let primaryMeas = "-";
    let secondaryMeas = "-";

    if (m.area_sq_meters != null) {
      primaryMeas = `<span class="font-semibold text-indigo-700">${formatNum(m.area_sq_meters)} m²</span>`;
      secondaryMeas = `${m.area_hectares} ha / ${m.area_sq_km} km²`;
    } else if (m.length_meters != null) {
      primaryMeas = `<span class="font-semibold text-sky-700">${formatNum(m.length_meters)} m</span>`;
      secondaryMeas = `${m.length_km} km`;
    } else if (m.measurement_status === "not_applicable") {
      primaryMeas = `<span class="text-amber-600 font-medium">N/A (Point)</span>`;
      secondaryMeas = "Coordinates recorded";
    } else {
      primaryMeas = `<span class="text-slate-400">${m.measurement_status || "Unsupported"}</span>`;
    }

    const propsPreview = Object.keys(f.properties).length > 0
      ? `<span class="font-mono text-slate-500" title='${JSON.stringify(f.properties)}'>${JSON.stringify(f.properties).substring(0, 35)}...</span>`
      : `<span class="text-slate-400">None</span>`;

    tr.innerHTML = `
      <td class="py-2.5 px-4 font-mono font-medium text-slate-800">${f.feature_id}</td>
      <td class="py-2.5 px-4"><span class="px-2 py-0.5 rounded text-[11px] font-semibold ${getBadgeColor(f.geometry_type)}">${f.geometry_type}</span></td>
      <td class="py-2.5 px-4">${primaryMeas}</td>
      <td class="py-2.5 px-4 text-slate-500">${secondaryMeas}</td>
      <td class="py-2.5 px-4 font-mono text-[11px] text-slate-600">${m.projected_crs || "-"}</td>
      <td class="py-2.5 px-4">${propsPreview}</td>
    `;
    tbody.appendChild(tr);
  });
}

function getBadgeColor(type) {
  const t = type.toUpperCase();
  if (t.includes("POLYGON")) return "bg-indigo-100 text-indigo-800";
  if (t.includes("LINE")) return "bg-sky-100 text-sky-800";
  if (t.includes("POINT")) return "bg-amber-100 text-amber-800";
  return "bg-slate-100 text-slate-700";
}

function formatNum(n) {
  if (n == null) return "0";
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function showStatus(msg, type) {
  const container = document.getElementById("status-container");
  container.classList.remove("hidden");
  let bg = "bg-blue-50 text-blue-800 border-blue-200";
  let icon = "fa-spinner fa-spin";

  if (type === "success") {
    bg = "bg-emerald-50 text-emerald-800 border-emerald-200";
    icon = "fa-circle-check";
  } else if (type === "error") {
    bg = "bg-rose-50 text-rose-800 border-rose-200";
    icon = "fa-circle-exclamation";
  }

  container.className = `mt-4 p-3 rounded-lg border text-xs flex items-center gap-2 ${bg}`;
  container.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${msg}</span>`;
}

function setupSampleButton() {
  document.getElementById("btn-sample-kml").addEventListener("click", () => {
    // Generate a rich sample KML blob and trigger upload
    const sampleKmlContent = `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Sample Geospatial Survey</name>
    <Placemark>
      <name>Central Park Reservoir (Polygon)</name>
      <description>Reservoir waterbody in New York City</description>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -73.9620,40.7850,0
              -73.9570,40.7865,0
              -73.9560,40.7830,0
              -73.9605,40.7815,0
              -73.9620,40.7850,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
    <Placemark>
      <name>5th Avenue Transect (LineString)</name>
      <description>Survey transect along 5th Ave</description>
      <LineString>
        <coordinates>
          -73.9680,40.7770,0
          -73.9640,40.7820,0
          -73.9600,40.7870,0
        </coordinates>
      </LineString>
    </Placemark>
    <Placemark>
      <name>Survey Benchmark Alpha (Point)</name>
      <description>Geodetic reference marker</description>
      <Point>
        <coordinates>-73.9625,40.7835,0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>`;

    const blob = new Blob([sampleKmlContent], { type: "application/vnd.google-earth.kml+xml" });
    const file = new File([blob], "sample_survey.kml", { type: "application/vnd.google-earth.kml+xml" });

    handleFileSelected(file);
    uploadAndProcessFile(file);
  });
}
