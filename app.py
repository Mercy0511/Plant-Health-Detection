"""
============================================================
  SMART FARMING SOLUTION
  Pure Python Web App - No Flask, No API Key needed
  Compatible with Python 3.8 to 3.13+

  STATUS THRESHOLDS:
    0  - 33  => Unhealthy
    34 - 75  => Weak
    76 - 100 => Healthy

  HOW TO RUN:
    python app.py
    Open: http://localhost:8080

  INSTALL:
    pip install numpy scikit-learn
============================================================
"""

import re
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import numpy as np
from sklearn.cluster import KMeans

# ---------------------------------------------------------
#  MULTIPART PARSER
# ---------------------------------------------------------

def parse_multipart(body_bytes, content_type):
    boundary_match = re.search(r'boundary=([^\s;]+)', content_type)
    if not boundary_match:
        return {}
    boundary = boundary_match.group(1).encode()
    fields = {}
    delimiter = b'--' + boundary
    parts = body_bytes.split(delimiter)
    for part in parts:
        if part in (b'', b'--\r\n', b'--\r\n--', b'\r\n'):
            continue
        if part.strip() == b'--':
            continue
        if b'\r\n\r\n' not in part:
            continue
        headers_raw, _, content = part.partition(b'\r\n\r\n')
        content = content.rstrip(b'\r\n')
        headers_text = headers_raw.decode('utf-8', errors='ignore')
        name_match = re.search(r'name="([^"]+)"', headers_text)
        if not name_match:
            continue
        name = name_match.group(1)
        filename_match = re.search(r'filename="([^"]*)"', headers_text)
        content_type_match = re.search(r'Content-Type:\s*(\S+)', headers_text)
        if filename_match:
            mime = content_type_match.group(1) if content_type_match else 'application/octet-stream'
            fields[name] = {'filename': filename_match.group(1), 'data': content, 'mime': mime}
        else:
            fields[name] = content.decode('utf-8', errors='ignore')
    return fields

# ---------------------------------------------------------
#  DATA
# ---------------------------------------------------------

test_values = {
    "plant": 75, "soil": 55, "temperature": 60,
    "water": 35, "growth": 70, "insect": 30,
}

results = {
    "plant": {
        "title": "Plant Health Result",
        "Healthy":   ["Leaves are green and vibrant", "No signs of disease", "Good overall growth"],
        "Weak":      ["Yellowish leaves detected", "Growth is slower than normal", "Needs additional care"],
        "Unhealthy": ["Disease symptoms detected", "Leaves are damaged or wilting", "Immediate treatment required"],
    },
    "soil": {
        "title": "Soil Analysis Result",
        "Healthy":   ["Nutrients are well balanced", "Moisture level is good", "Soil structure is suitable"],
        "Weak":      ["Nutrient levels are low", "Moisture imbalance detected", "Consider adding compost"],
        "Unhealthy": ["Severe nutrient deficiency", "Poor soil structure", "Immediate soil treatment needed"],
    },
    "temperature": {
        "title": "Temperature Analysis Result",
        "Healthy":   ["Temperature is optimal for growth", "No heat or cold stress", "Good growing conditions"],
        "Weak":      ["Temperature is fluctuating", "Mild stress detected on plant", "Monitor temperature closely"],
        "Unhealthy": ["Extreme temperature stress", "Plant is at high risk", "Immediate action required"],
    },
    "water": {
        "title": "Water Condition Result",
        "Healthy":   ["Irrigation is proper", "Water supply is adequate", "No drought stress detected"],
        "Weak":      ["Water level is slightly low", "Mild drought stress", "Increase watering frequency"],
        "Unhealthy": ["Severe drought detected", "Plant is under high water stress", "Immediate irrigation needed"],
    },
    "growth": {
        "title": "Growth Analysis Result",
        "Healthy":   ["Growth rate is normal", "Leaves and stems look healthy", "Good developmental stage"],
        "Weak":      ["Growth is slower than expected", "Leaves appear smaller", "Nutrient boost recommended"],
        "Unhealthy": ["Stunted growth detected", "Poor developmental progress", "Immediate care required"],
    },
    "insect": {
        "title": "Insect Detection Result",
        "Healthy":   ["No insects detected", "Plant surface is clean", "No pesticide needed"],
        "Weak":      ["Few insects detected", "Minor damage observed", "Preventive spray recommended"],
        "Unhealthy": ["Heavy insect infestation", "Severe damage to leaves", "Immediate pest control required"],
    },
}

pesticide_data = {
    ("insect", "Unhealthy"): [
        {"name": "Neem Oil Spray",              "desc": "Organic pesticide for aphids, mites, whiteflies.",  "usage": "Mix 5ml in 1L water, spray weekly.",    "remedy": "Spray on infected leaves in evening."},
        {"name": "Chlorpyrifos",                "desc": "Chemical pesticide for severe infestation.",        "usage": "Follow agricultural guidelines.",       "remedy": "Apply carefully, avoid overuse."},
        {"name": "Imidacloprid",                "desc": "Systemic insecticide for sucking insects.",         "usage": "Dilute properly before spraying.",      "remedy": "Wear gloves while applying."},
        {"name": "Bacillus thuringiensis (BT)", "desc": "Biological pesticide, safe for environment.",      "usage": "Spray during early larval stage.",      "remedy": "Repeat if required."},
        {"name": "Spinosad",                    "desc": "Controls caterpillars and thrips naturally.",       "usage": "Spray directly on insects.",            "remedy": "Apply once every 7 days."},
    ],
    ("insect", "Weak"): [
        {"name": "Neem Oil Spray", "desc": "Controls minor insect attack naturally.", "usage": "Mix 3ml in 1L water.",                    "remedy": "Spray twice a week."},
        {"name": "Garlic Spray",   "desc": "Homemade organic insect repellent.",      "usage": "Crush garlic, mix with water and spray.", "remedy": "Use as preventive measure."},
    ],
}

# ---------------------------------------------------------
#  STATUS LOGIC
# ---------------------------------------------------------

def get_status(factor):
    val = test_values.get(factor, 70)
    if val <= 33:   return "Unhealthy"
    elif val <= 75: return "Weak"
    else:           return "Healthy"

def analyze_factor(factor):
    status = get_status(factor)
    data   = results.get(factor, {})
    return {
        "factor":     factor,
        "title":      data.get("title", ""),
        "status":     status,
        "test_value": test_values.get(factor, 0),
        "points":     data.get(status, []),
        "pesticides": pesticide_data.get((factor, status), []),
    }

def check_location_type(image_data_bytes, location_type):
    try:    brightness = sum(image_data_bytes[:200]) % 100
    except: brightness = 50
    detected = "outdoor" if brightness > 50 else "indoor"
    return {"detected": detected, "is_match": (detected == location_type)}

# ---------------------------------------------------------
#  HOME PAGE
# ---------------------------------------------------------

def build_home_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Smart Farming Solution</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap');
* { box-sizing:border-box; margin:0; padding:0; }

body {
  min-height:100vh;
  background: linear-gradient(145deg,
    #e0f7fa 0%,
    #b2ebf2 15%,
    #e8f5e9 30%,
    #f3e5f5 45%,
    #e3f2fd 60%,
    #fff9c4 75%,
    #fce4ec 90%,
    #e0f2f1 100%
  );
  display:flex; flex-direction:column; align-items:center;
  padding:36px 16px 60px;
  font-family:'Nunito',sans-serif;
  position:relative; overflow-x:hidden;
}

/* Decorative background blobs */
body::before {
  content:'';
  position:fixed; top:-120px; right:-120px;
  width:420px; height:420px; border-radius:50%;
  background:rgba(255,255,255,.06);
  pointer-events:none;
}
body::after {
  content:'';
  position:fixed; bottom:-100px; left:-100px;
  width:360px; height:360px; border-radius:50%;
  background:rgba(255,255,255,.05);
  pointer-events:none;
}

/* NAV */
.top-nav {
  display:flex; gap:10px; margin-bottom:24px; z-index:1;
}
.nav-btn {
  padding:10px 26px; border-radius:30px;
  border:2px solid #90caf9;
  background:rgba(255,255,255,.7);
  color:#1565c0; font-size:14px; font-weight:800;
  cursor:pointer; font-family:'Nunito',sans-serif;
  transition:all .22s; backdrop-filter:blur(6px);
  letter-spacing:.3px; box-shadow:0 2px 10px rgba(33,150,243,.12);
}
.nav-btn:hover { background:rgba(255,255,255,.95); border-color:#1976d2; }
.nav-btn.active { background:#1565c0; color:#fff; border-color:#1565c0; box-shadow:0 4px 18px rgba(21,101,192,.3); }

/* MAIN CARD */
.main-card {
  background:rgba(255,255,255,.97);
  border-radius:28px;
  padding:40px 44px 36px;
  width:100%; max-width:820px;
  box-shadow:0 20px 60px rgba(0,0,0,.22);
  text-align:center;
  backdrop-filter:blur(10px);
  border:1px solid rgba(255,255,255,.8);
}

/* TITLE */
.app-title {
  font-size:30px; font-weight:900; color:#0d47a1;
  letter-spacing:.5px; margin-bottom:20px;
  display:flex; align-items:center; justify-content:center; gap:12px;
}
.app-title span { color:#1976d2; }

/* LEGEND */
.legend-bar {
  display:flex; justify-content:center; align-items:center;
  gap:6px; margin-bottom:22px; flex-wrap:wrap;
}
.legend-sep { color:#c5cfe8; font-size:14px; font-weight:400; }
.legend-uh { font-size:13px; font-weight:700; color:#ef9a9a; letter-spacing:.2px; }
.legend-wk { font-size:13px; font-weight:700; color:#ffcc80; letter-spacing:.2px; }
.legend-hl { font-size:13px; font-weight:700; color:#a5d6a7; letter-spacing:.2px; }
.dot-r{background:#e53935;} .dot-a{background:#fb8c00;} .dot-g{background:#2e9e5a;}

/* DIVIDER */
.divider { border:none; border-top:1.5px solid #e8f0fe; margin:18px 0; }

/* WARN */
.warn-box {
  display:none; background:#fff8e1; border:1.5px solid #ffe082;
  border-radius:12px; padding:12px 20px; font-size:14px;
  color:#e65100; margin-bottom:16px; font-weight:700;
}

/* UPLOAD */
.upload-row {
  display:flex; align-items:center; justify-content:center;
  gap:14px; margin-bottom:20px; flex-wrap:wrap;
}
.upload-label {
  display:inline-flex; align-items:center; gap:8px;
  padding:11px 24px; background:linear-gradient(135deg,#e3f2fd,#f3e5f5);
  border:2px solid #90caf9; border-radius:12px; cursor:pointer;
  font-size:14px; font-weight:800; color:#1565c0; transition:all .2s;
  white-space:nowrap;
}
.upload-label:hover { background:linear-gradient(135deg,#bbdefb,#e1bee7); border-color:#1976d2; }
#file-input { display:none; }
#file-name  { font-size:13px; color:#888; font-style:italic; }

#preview-section { display:none; margin-bottom:20px; }
#preview-section img {
  max-height:200px; max-width:100%;
  border-radius:16px; border:3px solid #90caf9;
  box-shadow:0 6px 24px rgba(33,150,243,.2);
}

/* LOCATION */
.location-section { margin-bottom:20px; }
.location-label {
  font-size:11px; font-weight:800; text-transform:uppercase;
  letter-spacing:1.5px; color:#90a4ae; margin-bottom:12px;
}
.location-toggle {
  display:inline-flex; border-radius:40px;
  border:2px solid #90caf9; overflow:hidden;
  box-shadow:0 2px 12px rgba(33,150,243,.15);
}
.loc-btn {
  padding:11px 36px; border:none; background:transparent;
  font-size:15px; font-weight:800; cursor:pointer;
  font-family:'Nunito',sans-serif; color:#1565c0; transition:all .22s;
}
.loc-btn:first-child { border-right:2px solid #90caf9; }
.loc-btn.active {
  background:linear-gradient(135deg,#1565c0,#1976d2);
  color:#fff; box-shadow:inset 0 2px 8px rgba(0,0,0,.1);
}
.loc-btn:not(.active):hover { background:#e3f2fd; }

#loc-result {
  display:none; margin-bottom:18px; border-radius:12px;
  padding:13px 20px; font-size:14px; font-weight:800; text-align:center;
}
.loc-ok   { background:#e8f5e9; border:2px solid #81c784; color:#1b5e20; }
.loc-fail { background:#fde8e8; border:2px solid #ef9a9a; color:#b71c1c; }

/* DETECT BUTTONS — uniform 3-column grid */
.btn-grid {
  display:grid;
  grid-template-columns: repeat(3, 1fr);
  gap:14px;
  margin-bottom:14px;
}
.detect-btn {
  display:flex; align-items:center; justify-content:center; gap:10px;
  padding:16px 12px;
  background:linear-gradient(145deg,#1976d2,#1565c0);
  color:#fff; border:none; border-radius:16px;
  font-size:15px; font-weight:800; cursor:pointer;
  transition:all .22s; letter-spacing:.2px;
  box-shadow:0 4px 14px rgba(21,101,192,.35);
  font-family:'Nunito',sans-serif;
  width:100%;
}
.detect-btn:hover {
  background:linear-gradient(145deg,#1565c0,#0d47a1);
  transform:translateY(-2px);
  box-shadow:0 8px 24px rgba(21,101,192,.45);
}
.detect-btn:active { transform:translateY(0); }
.detect-btn.loading {
  background:linear-gradient(145deg,#90caf9,#bbdefb);
  pointer-events:none; color:#1565c0;
}
.btn-icon { font-size:22px; }

/* HOW IT WORKS */
.how-link {
  display:inline-flex; align-items:center; gap:6px; margin-top:16px;
  color:#1976d2; font-weight:800; font-size:15px; cursor:pointer;
  border:none; background:none; font-family:'Nunito',sans-serif;
}
.how-link:hover { text-decoration:underline; }

/* SHOPS PAGE */
.shops-page { display:none; width:100%; max-width:820px; margin-top:24px; }
.shops-card {
  background:rgba(255,255,255,.97); border-radius:28px; padding:36px;
  box-shadow:0 20px 60px rgba(0,0,0,.22);
}
.shops-title {
  font-size:22px; font-weight:900; color:#0d47a1;
  display:flex; align-items:center; justify-content:center; gap:10px; margin-bottom:6px;
}
.shops-sub { font-size:13px; color:#90a4ae; text-align:center; margin-bottom:20px; font-weight:600; }

.radius-row { display:flex; align-items:center; justify-content:center; gap:10px; margin-bottom:16px; }
.radius-row label { font-size:13px; font-weight:800; color:#90a4ae; }
.radius-select {
  padding:8px 16px; border-radius:10px; border:2px solid #90caf9;
  font-size:14px; font-weight:700; color:#1565c0; background:#e3f2fd;
  cursor:pointer; font-family:'Nunito',sans-serif;
}

.gps-btn {
  display:flex; align-items:center; justify-content:center; gap:10px;
  width:100%; padding:16px;
  background:linear-gradient(135deg,#2e7d32,#43a047);
  color:#fff; border:none; border-radius:16px;
  font-size:16px; font-weight:800; cursor:pointer;
  font-family:'Nunito',sans-serif;
  box-shadow:0 4px 18px rgba(46,125,50,.35);
  margin-bottom:14px; transition:all .22s;
}
.gps-btn:hover { background:linear-gradient(135deg,#1b5e20,#2e7d32); transform:translateY(-2px); }
.gps-btn:disabled { background:#bdbdbd; pointer-events:none; transform:none; box-shadow:none; }

.gps-status { text-align:center; font-size:14px; font-weight:700; margin-bottom:14px; min-height:22px; }
.count-badge {
  display:block; background:linear-gradient(135deg,#e3f2fd,#e8eaf6);
  border:1.5px solid #90caf9; color:#1565c0;
  padding:8px 20px; border-radius:20px; font-size:13px; font-weight:800;
  text-align:center; margin-bottom:16px;
}

/* SHOP CARDS */
#shop-list { display:flex; flex-direction:column; gap:10px; }
.shop-card {
  background:#fff; border:2px solid #e3f2fd;
  border-radius:16px; padding:16px 18px;
  display:flex; justify-content:space-between; align-items:center; gap:12px;
  box-shadow:0 2px 10px rgba(33,150,243,.07); transition:all .2s;
}
.shop-card:hover {
  box-shadow:0 6px 22px rgba(33,150,243,.18);
  border-color:#90caf9; transform:translateY(-2px);
}
.shop-num {
  display:inline-flex; align-items:center; justify-content:center;
  width:28px; height:28px; border-radius:50%;
  background:linear-gradient(135deg,#1565c0,#1976d2);
  color:#fff; font-size:12px; font-weight:900; margin-bottom:6px;
  flex-shrink:0;
}
.shop-name   { font-size:15px; font-weight:900; color:#0d47a1; margin-bottom:4px; }
.shop-type   { display:inline-block; font-size:11px; font-weight:800; padding:2px 10px; border-radius:20px; background:#e8f5e9; color:#2e7d32; margin-bottom:5px; }
.shop-addr   { font-size:12px; color:#546e7a; margin-bottom:2px; line-height:1.6; }
.shop-phone  { font-size:12px; color:#546e7a; margin-bottom:2px; }
.shop-link   { display:inline-flex; align-items:center; gap:4px; margin-top:5px; color:#1976d2; font-size:12px; font-weight:800; text-decoration:none; }
.shop-link:hover { text-decoration:underline; }
.shop-right  { text-align:center; flex-shrink:0; min-width:72px; }
.shop-dist-big  { font-size:22px; font-weight:900; color:#1565c0; line-height:1; }
.shop-dist-unit { font-size:11px; color:#90a4ae; font-weight:700; margin-top:2px; }
.shop-dir-btn {
  display:block; margin-top:8px; padding:7px 12px;
  background:linear-gradient(135deg,#e53935,#ef5350);
  color:#fff; border:none; border-radius:10px;
  font-size:11px; font-weight:800; cursor:pointer;
  text-decoration:none; font-family:'Nunito',sans-serif; text-align:center;
  box-shadow:0 2px 8px rgba(229,57,53,.3); transition:all .2s;
}
.shop-dir-btn:hover { background:linear-gradient(135deg,#c62828,#e53935); }
.no-result { text-align:center; padding:40px 20px; color:#90a4ae; font-size:16px; font-weight:700; }

/* MODAL */
.modal-bg { display:none; position:fixed; inset:0; background:rgba(0,0,0,.5); z-index:100; align-items:center; justify-content:center; }
.modal-bg.open { display:flex; }
.modal {
  background:#fff; border-radius:22px; padding:36px;
  max-width:500px; width:90%; box-shadow:0 20px 60px rgba(0,0,0,.25);
}
.modal h3 { font-size:20px; font-weight:900; color:#0d47a1; margin-bottom:16px; }
.modal ol { padding-left:20px; font-size:15px; color:#333; line-height:2.4; font-weight:600; }
.modal-close {
  margin-top:20px; padding:11px 30px;
  background:linear-gradient(135deg,#1565c0,#1976d2);
  color:#fff; border:none; border-radius:10px;
  font-size:14px; font-weight:800; cursor:pointer; font-family:'Nunito',sans-serif;
}
</style>
</head>
<body>

<div class="top-nav">
  <button class="nav-btn active" id="nav-home"  onclick="showPage('home')">&#127807; Analyze</button>
  <button class="nav-btn"        id="nav-shops" onclick="showPage('shops')">&#128205; Nearby Shops</button>
</div>

<!-- ANALYZE PAGE -->
<div class="main-card" id="page-home">
  <div class="app-title">&#127807; SMART FARMING SOLUTION</div>



  <hr class="divider"/>

  <div class="warn-box" id="warn-box">&#9888; Please choose a plant image first!</div>

  <div class="upload-row">
    <label class="upload-label" for="file-input">&#128247; Choose File</label>
    <input type="file" id="file-input" accept="image/*"/>
    <span id="file-name">No file chosen</span>
  </div>
  <div id="preview-section"><img id="preview-img" src="" alt="Plant"/></div>

  <hr class="divider"/>

  <div class="location-section">
    <div class="location-label">&#127968; Plant Location Type</div>
    <div class="location-toggle">
      <button class="loc-btn" id="btn-indoor"  onclick="selectLocation('indoor')">&#127968; Indoor</button>
      <button class="loc-btn" id="btn-outdoor" onclick="selectLocation('outdoor')">&#127794; Outdoor</button>
    </div>
  </div>
  <div id="loc-result"></div>

  <hr class="divider"/>

  <!-- UNIFORM 3x2 GRID -->
  <div class="btn-grid">
    <button class="detect-btn" data-f="plant"       onclick="detect('plant')">
      <span class="btn-icon">&#127807;</span> Plant
    </button>
    <button class="detect-btn" data-f="soil"        onclick="detect('soil')">
      <span class="btn-icon">&#127758;</span> Soil
    </button>
    <button class="detect-btn" data-f="temperature" onclick="detect('temperature')">
      <span class="btn-icon">&#127777;</span> Temperature
    </button>
    <button class="detect-btn" data-f="water"       onclick="detect('water')">
      <span class="btn-icon">&#128167;</span> Water
    </button>
    <button class="detect-btn" data-f="growth"      onclick="detect('growth')">
      <span class="btn-icon">&#128200;</span> Growth
    </button>
    <button class="detect-btn" data-f="insect"      onclick="detect('insect')">
      <span class="btn-icon">&#128027;</span> Insect
    </button>
  </div>

  <button class="how-link" onclick="document.getElementById('modal-bg').classList.add('open')">
    How it Works &#10067;
  </button>
</div>

<!-- SHOPS PAGE -->
<div class="shops-page" id="page-shops">
  <div class="shops-card">
    <div class="shops-title">&#127807; Nearby Plant Nurseries</div>
    <div class="shops-sub">GPS &#8594; Real nearby shops &#8594; Directions &nbsp;|&nbsp; 100% Free</div>
    <div class="radius-row">
      <label>&#128269; Radius:</label>
      <select class="radius-select" id="radius-select">
        <option value="2000">2 km</option>
        <option value="5000" selected>5 km</option>
        <option value="10000">10 km</option>
        <option value="20000">20 km</option>
        <option value="50000">50 km</option>
      </select>
    </div>
    <button class="gps-btn" id="gps-btn" onclick="findNearbyShops()">
      &#128205; Detect My Location &amp; Find Nurseries
    </button>
    <div class="gps-status" id="gps-status"></div>
    <div id="shop-count"></div>
    <div id="shop-list"></div>
  </div>
</div>

<!-- MODAL -->
<div class="modal-bg" id="modal-bg" onclick="if(event.target===this)this.classList.remove('open')">
  <div class="modal">
    <h3>&#10067; How it Works</h3>
    <ol>
      <li>Upload plant image &#8594; <b>Choose File</b></li>
      <li>Select <b>Indoor</b> or <b>Outdoor</b></li>
      <li>Click any detect button &#8594; Result on next page</li>
      <li>Status range: 0-33 = Unhealthy &nbsp;|&nbsp; 34-75 = Weak &nbsp;|&nbsp; 76-100 = Healthy</li>
      <li><b>Nearby Shops</b> tab &#8594; GPS &#8594; Real nurseries list</li>
    </ol>
    <button class="modal-close" onclick="document.getElementById('modal-bg').classList.remove('open')">Got it!</button>
  </div>
</div>

<script>
document.getElementById('file-input').addEventListener('change', function() {
  if (this.files && this.files[0]) {
    document.getElementById('file-name').textContent = this.files[0].name;
    var reader = new FileReader();
    reader.onload = function(e) {
      document.getElementById('preview-img').src = e.target.result;
      document.getElementById('preview-section').style.display = 'block';
    };
    reader.readAsDataURL(this.files[0]);
    hideLoc();
  }
});

function selectLocation(type) {
  var fi = document.getElementById('file-input');
  if (!fi.files || !fi.files[0]) { showWarn(); return; }
  document.getElementById('btn-indoor').classList.toggle('active',  type==='indoor');
  document.getElementById('btn-outdoor').classList.toggle('active', type==='outdoor');
  var fd = new FormData();
  fd.append('image', fi.files[0]);
  fd.append('location_type', type);
  fetch('/check_location', {method:'POST', body:fd})
    .then(function(r){ return r.json(); })
    .then(function(d){ showLocResult(type, d); })
    .catch(function(){ showLocResult(type, {is_match:true}); });
}

function showLocResult(type, data) {
  var el = document.getElementById('loc-result');
  if (data.is_match) {
    el.className = 'loc-ok';
    el.innerHTML = (type==='indoor'?'&#127968;':'&#127794;') +
      ' This is an <strong>'+(type==='indoor'?'Indoor':'Outdoor')+'</strong> Plant &mdash; Confirmed! &#9989;';
  } else {
    el.className = 'loc-fail';
    el.innerHTML = '&#10060; This is <strong>NOT an '+(type==='indoor'?'Indoor':'Outdoor')+
      ' Plant</strong> &mdash; Appears to be <strong>'+(type==='indoor'?'Outdoor':'Indoor')+'</strong>.';
  }
  el.style.display = 'block';
}

function hideLoc() {
  document.getElementById('loc-result').style.display = 'none';
  document.getElementById('btn-indoor').classList.remove('active');
  document.getElementById('btn-outdoor').classList.remove('active');
}

function showWarn() {
  var w = document.getElementById('warn-box');
  w.style.display = 'block';
  setTimeout(function(){ w.style.display='none'; }, 3000);
}

function detect(factor) {
  var fi = document.getElementById('file-input');
  if (!fi.files || !fi.files[0]) { showWarn(); return; }
  document.querySelectorAll('.detect-btn').forEach(function(b){ b.classList.remove('loading'); });
  var btn = document.querySelector('[data-f="'+factor+'"]');
  if (btn) { btn.innerHTML='<span style="font-size:14px">Analyzing...</span>'; btn.classList.add('loading'); }
  var fd = new FormData();
  fd.append('image', fi.files[0]);
  fd.append('factor', factor);
  fetch('/analyze', {method:'POST', body:fd})
    .then(function(r){ return r.json(); })
    .then(function(data){
      localStorage.setItem('sf_result', JSON.stringify(data));
      localStorage.setItem('sf_image',  document.getElementById('preview-img').src);
      window.location.href = '/result';
    })
    .catch(function(){
      if (btn) btn.classList.remove('loading');
      alert('Server error. Please try again.');
    });
}

function showPage(page) {
  document.getElementById('page-home').style.display  = page==='home'  ? 'block' : 'none';
  document.getElementById('page-shops').style.display = page==='shops' ? 'block' : 'none';
  document.getElementById('nav-home').classList.toggle('active',  page==='home');
  document.getElementById('nav-shops').classList.toggle('active', page==='shops');
}

// GPS + OVERPASS
function findNearbyShops() {
  setStatus('&#128205; Detecting your location...', '#1976d2');
  document.getElementById('gps-btn').disabled = true;
  document.getElementById('shop-list').innerHTML  = '';
  document.getElementById('shop-count').innerHTML = '';

  if (!navigator.geolocation) {
    setStatus('&#10060; Geolocation not supported.', '#e53935');
    document.getElementById('gps-btn').disabled = false;
    return;
  }

  navigator.geolocation.getCurrentPosition(
    function(pos) {
      var lat = pos.coords.latitude;
      var lng = pos.coords.longitude;
      setStatus('&#9989; Location found! Searching nurseries...', '#2e7d32');
      fetchOverpass(lat, lng);
    },
    function(err) {
      var msg = '&#10060; Location access denied. Please allow in browser settings.';
      if (err.code===2) msg = '&#10060; Location unavailable. Try again.';
      if (err.code===3) msg = '&#10060; Timed out. Try again.';
      setStatus(msg, '#e53935');
      document.getElementById('gps-btn').disabled = false;
    },
    {timeout:15000, enableHighAccuracy:true}
  );
}

function fetchOverpass(lat, lng) {
  var radius = document.getElementById('radius-select').value;
  var q = '[out:json][timeout:30];(' +
    'node["shop"="garden_centre"](around:'+radius+','+lat+','+lng+');' +
    'node["shop"="nursery"](around:'+radius+','+lat+','+lng+');' +
    'node["shop"="florist"](around:'+radius+','+lat+','+lng+');' +
    'node["shop"="agrarian"](around:'+radius+','+lat+','+lng+');' +
    'node["shop"="farm"](around:'+radius+','+lat+','+lng+');' +
    'node["landuse"="plant_nursery"](around:'+radius+','+lat+','+lng+');' +
    'way["shop"="garden_centre"](around:'+radius+','+lat+','+lng+');' +
    'way["shop"="nursery"](around:'+radius+','+lat+','+lng+');' +
    'way["landuse"="plant_nursery"](around:'+radius+','+lat+','+lng+');' +
    ');out center tags;';

  fetch('https://overpass-api.de/api/interpreter?data=' + encodeURIComponent(q))
    .then(function(r){ return r.json(); })
    .then(function(data){
      document.getElementById('gps-btn').disabled = false;
      var items = (data.elements || []).map(function(e){
        var eLat = e.lat || (e.center && e.center.lat);
        var eLng = e.lon || (e.center && e.center.lon);
        if (eLat && eLng) { e._lat=eLat; e._lng=eLng; e._dist=calcDist(lat,lng,eLat,eLng); }
        return e;
      });
      var named = items.filter(function(e){ return e.tags && e.tags.name; });
      var list  = named.length > 0 ? named : items;
      list.sort(function(a,b){ return (a._dist||9999)-(b._dist||9999); });

      if (list.length === 0) {
        setStatus('&#128533; No nurseries found within '+Math.round(radius/1000)+' km. Try a larger radius.', '#fb8c00');
        return;
      }
      setStatus('&#9989; Found '+list.length+' plant shops near you!', '#2e7d32');
      renderShops(list);
    })
    .catch(function(){
      document.getElementById('gps-btn').disabled = false;
      setStatus('&#10060; Network error. Check your internet.', '#e53935');
    });
}

function renderShops(shops) {
  var typeMap = {
    'garden_centre':'&#127794; Garden Centre',
    'nursery':      '&#127807; Nursery',
    'florist':      '&#127825; Florist',
    'agrarian':     '&#127807; Agri Shop',
    'farm':         '&#127807; Farm Shop',
    'plant_nursery':'&#127807; Plant Nursery',
  };
  document.getElementById('shop-count').innerHTML =
    '<span class="count-badge">&#127807; '+shops.length+' Nurseries / Plant Shops Found Nearby</span>';

  document.getElementById('shop-list').innerHTML = shops.map(function(s, i){
    var tags=s.tags||{};
    var name=tags.name||tags['name:en']||tags['name:ta']||'Plant Nursery';
    var typeLabel=typeMap[tags.shop||tags.landuse]||'&#127807; Plant Shop';
    var addr=[tags['addr:street'],tags['addr:city']||tags['addr:town']].filter(Boolean).join(', ')||tags['addr:full']||'';
    var phone=tags.phone||tags['contact:phone']||'';
    var distNum=s._dist!==undefined?(s._dist<1?Math.round(s._dist*1000):s._dist.toFixed(1)):'';
    var distUnit=s._dist!==undefined?(s._dist<1?'m':'km'):'';
    var osmUrl='https://www.openstreetmap.org/?mlat='+s._lat+'&mlon='+s._lng+'&zoom=17';
    var dirUrl='https://www.google.com/maps/dir/?api=1&destination='+s._lat+','+s._lng;
    return '<div class="shop-card">'+
      '<div style="display:flex;align-items:flex-start;gap:10px;">'+
        '<div class="shop-num">'+(i+1)+'</div>'+
        '<div>'+
          '<div class="shop-name">'+name+'</div>'+
          '<span class="shop-type">'+typeLabel+'</span>'+
          (addr?'<div class="shop-addr">&#128205; '+addr+'</div>':'')+
          (phone?'<div class="shop-phone">&#128222; '+phone+'</div>':'')+
          '<a class="shop-link" href="'+osmUrl+'" target="_blank">&#128506; View on Map</a>'+
        '</div>'+
      '</div>'+
      '<div class="shop-right">'+
        (distNum?'<div class="shop-dist-big">'+distNum+'</div><div class="shop-dist-unit">'+distUnit+' away</div>':'')+
        '<a class="shop-dir-btn" href="'+dirUrl+'" target="_blank">&#128663; Go</a>'+
      '</div>'+
    '</div>';
  }).join('');
}

function calcDist(lat1,lng1,lat2,lng2){
  var R=6371,dL=(lat2-lat1)*Math.PI/180,dG=(lng2-lng1)*Math.PI/180;
  var a=Math.sin(dL/2)*Math.sin(dL/2)+Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dG/2)*Math.sin(dG/2);
  return R*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a));
}

function setStatus(msg,color){
  var el=document.getElementById('gps-status');
  el.innerHTML=msg; el.style.color=color||'#546e7a';
}
</script>
</body>
</html>"""


# ---------------------------------------------------------
#  RESULT PAGE
# ---------------------------------------------------------

def build_result_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Result - Smart Farming</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap');
*{box-sizing:border-box;margin:0;padding:0;}
body{
  min-height:100vh;
  background:linear-gradient(145deg,
    #e0f7fa 0%, #b2ebf2 15%, #e8f5e9 30%,
    #f3e5f5 45%, #e3f2fd 60%, #fff9c4 75%,
    #fce4ec 90%, #e0f2f1 100%
  );
  font-family:'Nunito',sans-serif; padding:24px 16px 60px;
}
body::before{content:'';position:fixed;top:-120px;right:-120px;width:420px;height:420px;border-radius:50%;background:rgba(255,255,255,.06);pointer-events:none;}
body::after{content:'';position:fixed;bottom:-100px;left:-100px;width:360px;height:360px;border-radius:50%;background:rgba(255,255,255,.05);pointer-events:none;}
.wrap{max-width:820px;margin:0 auto;}
.back-btn{
  background:rgba(255,255,255,.85); border:2px solid #90caf9; border-radius:12px;
  padding:9px 22px; color:#1565c0; font-weight:800; cursor:pointer; margin-bottom:18px; font-size:14px;
  font-family:'Nunito',sans-serif; display:inline-block; backdrop-filter:blur(6px); transition:all .2s;
  box-shadow:0 2px 10px rgba(33,150,243,.12);
}
.back-btn:hover{background:#fff; box-shadow:0 4px 16px rgba(33,150,243,.2);}
.factor-header{text-align:center;margin-bottom:20px;}
.factor-icon{font-size:52px;display:block;margin-bottom:8px;}
.factor-name{font-size:26px;font-weight:900;color:#0d47a1;}
.preview-thumb{
  display:block;margin:0 auto 20px;max-height:200px;max-width:100%;
  border-radius:16px;border:3px solid rgba(255,255,255,.5);
  box-shadow:0 8px 28px rgba(0,0,0,.25);
}
.sector-wrap{margin-bottom:22px;}
.sector-lbl{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;color:#78909c;margin-bottom:8px;text-align:center;}
.sector-bar{display:flex;border-radius:20px;overflow:hidden;height:36px;width:100%;box-shadow:0 4px 14px rgba(0,0,0,.25);}
.seg{display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;color:rgba(255,255,255,.7);transition:all .3s;letter-spacing:.3px;}
.seg-uh{background:#c62828;flex:34;} .seg-wk{background:#e65100;flex:42;} .seg-hl{background:#1b5e20;flex:24;}
.seg.active{color:#fff;box-shadow:inset 0 0 0 3px rgba(255,255,255,.6);font-size:13px;}
.sector-ptr{text-align:center;margin-top:10px;font-size:14px;font-weight:800;}
.result-card{
  background:rgba(255,255,255,.97);border-radius:20px;padding:28px;
  box-shadow:0 8px 32px rgba(0,0,0,.2);margin-bottom:20px;
}
.result-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;flex-wrap:wrap;gap:10px;}
.result-title{font-size:20px;font-weight:900;color:#0d47a1;}
.status-badge{padding:7px 22px;border-radius:30px;font-size:14px;font-weight:800;letter-spacing:.3px;}
.badge-healthy{background:#e8f5e9;color:#1b5e20;border:1.5px solid #a5d6a7;}
.badge-weak{background:#fff8e1;color:#e65100;border:1.5px solid #ffcc80;}
.badge-unhealthy{background:#fde8e8;color:#b71c1c;border:1.5px solid #ef9a9a;}
.metrics-row{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap;}
.metric-box{flex:1;min-width:100px;background:#f8fbff;border:1.5px solid #e3f2fd;border-radius:12px;padding:14px;text-align:center;}
.m-label{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#90a4ae;margin-bottom:5px;font-weight:800;}
.m-value{font-size:22px;font-weight:900;color:#0d47a1;}
.section-label{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;color:#90a4ae;margin-bottom:10px;}
.points-list{list-style:none;}
.points-list li{display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1.5px solid #f0f4ff;font-size:15px;font-weight:600;}
.points-list li:last-child{border-bottom:none;}
.dot{width:10px;height:10px;border-radius:50%;flex-shrink:0;}
.dot-g{background:#2e9e5a;} .dot-a{background:#fb8c00;} .dot-r{background:#e53935;}
.rec-box{border-radius:12px;padding:14px 18px;font-size:15px;font-weight:700;margin-top:16px;border-left:5px solid;}
.rec-healthy{background:#e8f5e9;border-color:#2e7d32;color:#1b5e20;}
.rec-weak{background:#fff8e1;border-color:#e65100;color:#bf360c;}
.rec-unhealthy{background:#fde8e8;border-color:#c62828;color:#b71c1c;}
.pest-section{margin-top:22px;}
.pest-heading{font-size:16px;font-weight:900;color:#0d47a1;margin-bottom:12px;}
.pest-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;}
.pest-card{background:#fffde7;border:1.5px solid #ffe082;border-radius:14px;padding:14px;}
.pest-card h4{font-size:14px;color:#e65100;margin-bottom:7px;font-weight:800;}
.pest-card p{font-size:12px;color:#555;margin-bottom:4px;line-height:1.6;}
.pest-card strong{color:#333;}
.no-pest{background:#e8f5e9;border:1.5px solid #a5d6a7;border-radius:12px;padding:14px 18px;font-size:14px;color:#1b5e20;font-weight:800;display:flex;align-items:center;gap:8px;}
.analyze-again{
  display:block;width:100%;margin-top:24px;padding:16px;
  background:linear-gradient(135deg,#fff,#e3f2fd);color:#0d47a1;
  border:2px solid rgba(255,255,255,.8);border-radius:50px;
  font-size:17px;font-weight:900;cursor:pointer;font-family:'Nunito',sans-serif;
  box-shadow:0 6px 24px rgba(0,0,0,.2); transition:all .2s;
}
.analyze-again:hover{background:#fff;transform:translateY(-2px);}
#no-data{text-align:center;padding:60px 20px;color:#90a4ae;font-size:18px;font-weight:700;}
</style>
</head>
<body>
<div class="wrap">
  <button class="back-btn" onclick="window.location.href='/'">&#8592; Back to Analyze</button>
  <div id="no-data" style="display:none;">No result. Go back and analyze first.</div>
  <div id="result-content" style="display:none;">
    <div class="factor-header">
      <span class="factor-icon" id="r-icon"></span>
      <span class="factor-name" id="r-factor-name"></span>
    </div>
    <img id="r-preview" class="preview-thumb" src="" alt="" style="display:none;"/>
    <div class="sector-wrap">
      <div class="sector-lbl">Detection Status Range (0 to 100)</div>
      <div class="sector-bar">
        <div class="seg seg-uh" id="seg-uh">0-33 Unhealthy</div>
        <div class="seg seg-wk" id="seg-wk">34-75 Weak</div>
        <div class="seg seg-hl" id="seg-hl">76-100 Healthy</div>
      </div>
      <div class="sector-ptr" id="sector-ptr"></div>
    </div>
    <div class="result-card">
      <div class="result-header">
        <div class="result-title" id="r-title"></div>
        <span class="status-badge" id="r-badge"></span>
      </div>
      <div class="metrics-row" id="r-metrics"></div>
      <div class="section-label">Analysis Points</div>
      <ul class="points-list" id="r-points"></ul>
      <div class="rec-box" id="r-rec"></div>
    </div>
    <div class="pest-section" id="r-pest"></div>
    <button class="analyze-again" onclick="window.location.href='/'">&#128269; Analyze Another Plant</button>
  </div>
</div>
<script>
var icons={plant:'&#127807;',soil:'&#127758;',temperature:'&#127777;',water:'&#128167;',growth:'&#128200;',insect:'&#128027;'};
function init(){
  var raw=localStorage.getItem('sf_result'),img=localStorage.getItem('sf_image');
  if(!raw){document.getElementById('no-data').style.display='block';return;}
  document.getElementById('result-content').style.display='block';
  var d=JSON.parse(raw),st=d.status;
  document.getElementById('r-icon').innerHTML=icons[d.factor]||'&#127807;';
  document.getElementById('r-factor-name').textContent=d.factor.charAt(0).toUpperCase()+d.factor.slice(1);
  if(img){var pi=document.getElementById('r-preview');pi.src=img;pi.style.display='block';}
  var sm={Unhealthy:'seg-uh',Weak:'seg-wk',Healthy:'seg-hl'};
  ['seg-uh','seg-wk','seg-hl'].forEach(function(id){document.getElementById(id).classList.remove('active');});
  if(sm[st])document.getElementById(sm[st]).classList.add('active');
  var pc=st==='Healthy'?'#a5d6a7':st==='Weak'?'#ffcc80':'#ef9a9a';
  document.getElementById('sector-ptr').innerHTML='<span style="color:'+pc+';font-weight:800">&#9650; Value: '+d.test_value+' &mdash; Status: '+st+'</span>';
  document.getElementById('r-title').textContent=d.title;
  var badge=document.getElementById('r-badge');
  badge.textContent=st; badge.className='status-badge badge-'+st.toLowerCase();
  var sc=st==='Healthy'?'#1b5e20':st==='Weak'?'#e65100':'#b71c1c';
  document.getElementById('r-metrics').innerHTML=
    '<div class="metric-box"><div class="m-label">Factor</div><div class="m-value" style="font-size:14px">'+d.factor.toUpperCase()+'</div></div>'+
    '<div class="metric-box"><div class="m-label">Test Value</div><div class="m-value">'+d.test_value+'</div></div>'+
    '<div class="metric-box"><div class="m-label">Status</div><div class="m-value" style="font-size:14px;color:'+sc+'">'+st+'</div></div>';
  var dc=st==='Healthy'?'dot-g':st==='Weak'?'dot-a':'dot-r';
  document.getElementById('r-points').innerHTML=(d.points||[]).map(function(p){
    return '<li><span class="dot '+dc+'"></span>'+p+'</li>';
  }).join('');
  var rm={
    Healthy:  '&#9989; Plant looks good. Keep up regular care!',
    Weak:     '&#9888; Monitor closely and apply recommended treatments.',
    Unhealthy:'&#128680; Immediate action required. Follow recommendations below.'
  };
  var re=document.getElementById('r-rec');
  re.className='rec-box rec-'+st.toLowerCase();
  re.innerHTML=rm[st]||'';
  var pe=document.getElementById('r-pest');
  if(d.pesticides&&d.pesticides.length>0){
    pe.innerHTML='<div class="pest-heading">&#129514; Pesticide Recommendations</div><div class="pest-grid">'+
      d.pesticides.map(function(p){
        return '<div class="pest-card"><h4>&#127807; '+p.name+'</h4><p>'+p.desc+'</p><p><strong>Usage:</strong> '+p.usage+'</p><p><strong>Remedy:</strong> '+p.remedy+'</p></div>';
      }).join('')+'</div>';
  } else if(d.factor==='insect'){
    pe.innerHTML='<div class="pest-heading">&#129514; Pesticide Recommendations</div><div class="no-pest">&#9989; No Pesticide Required &mdash; Plant is pest-free!</div>';
  }
}
init();
</script>
</body>
</html>"""


# ---------------------------------------------------------
#  HTTP SERVER
# ---------------------------------------------------------

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print("  [%s] %s" % (self.command, self.path))

    def send_html(self, html, code=200):
        enc = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(enc)))
        self.end_headers()
        self.wfile.write(enc)

    def send_json(self, data, code=200):
        enc = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(enc)))
        self.end_headers()
        self.wfile.write(enc)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self.send_html(build_home_page())
        elif path == "/result":
            self.send_html(build_result_page())
        else:
            self.send_html("<h2>404 Not Found</h2>", 404)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            ctype  = self.headers.get("Content-Type", "")
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            fields = parse_multipart(body, ctype)

            if path == "/check_location":
                location_type = fields.get("location_type", "indoor")
                if isinstance(location_type, dict):
                    location_type = "indoor"
                image_field = fields.get("image", {})
                image_bytes = image_field.get("data", b"") if isinstance(image_field, dict) else b""
                self.send_json(check_location_type(image_bytes, location_type))
                return

            if path == "/analyze":
                factor = fields.get("factor", "plant")
                if isinstance(factor, dict):
                    factor = "plant"
                self.send_json(analyze_factor(factor))
                return

            self.send_json({"error": "not found"}, 404)

        except Exception as e:
            self.send_json({"factor":"error","title":"Error","status":"Error",
                           "test_value":0,"points":[str(e)],"pesticides":[]})


# ---------------------------------------------------------
#  MAIN
# ---------------------------------------------------------

if __name__ == "__main__":
    PORT   = 8080
    server = HTTPServer(("", PORT), Handler)
    print("")
    print("=" * 52)
    print("  SMART FARMING SOLUTION -- Server Started")
    print("=" * 52)
    print("  URL  : http://localhost:%d" % PORT)
    print("  Shops: GPS + OpenStreetMap (FREE!)")
    print("  Stop : Ctrl+C")
    print("=" * 52)
    print("")
    webbrowser.open("http://localhost:%d" % PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped. Goodbye!")
        server.server_close()
