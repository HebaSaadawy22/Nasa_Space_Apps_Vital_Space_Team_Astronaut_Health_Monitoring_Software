"use strict";
const $ = id => document.getElementById(id), R = Math.PI / 180;
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const wrap180 = x => ((x + 180) % 360 + 360) % 360 - 180;           // always returns [-180, 180)
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
// Sizes a canvas to its CSS box (x devicePixelRatio) and only touches it when the size really changed
function fit(c) {
  const r = c.getBoundingClientRect(), d = devicePixelRatio || 1, W = Math.round(r.width * d), H = Math.round(r.height * d);
  if (c.width !== W || c.height !== H) { c.width = W; c.height = H; }
  return [W, H, d];
}

/* ---------- Crew & metrics ---------- */
const CAB = { o2: 20.9, co2: 2600, press: 101.3, hum: 45 };
const CREW = [
  { n: "Cdr. Nora Hale", day: 142, mod: 3, b: { hr: 68, spo2: 98, sys: 112, dia: 72, temp: 36.7, resp: 15, rad: .55, sleep: 7.2, stress: 28, bone: 1.4, muscle: 96 } },
  { n: "Eng. Adam Reyes", day: 87, mod: 0, b: { hr: 74, spo2: 97, sys: 118, dia: 76, temp: 36.8, resp: 16, rad: .7, sleep: 6.4, stress: 42, bone: 1.2, muscle: 95 } },
  { n: "Dr. Leo Marsh", day: 201, mod: 4, b: { hr: 80, spo2: 96, sys: 124, dia: 82, temp: 37, resp: 18, rad: .65, sleep: 5.6, stress: 61, bone: 2.6, muscle: 91 } }
];
// g: v = vitals, s = space effects, e = cabin environment
const M = [
  { k: "hr", t: "Heart rate", u: "bpm", lo: 60, hi: 100, d: 0, j: 3, g: "v" },
  { k: "spo2", t: "Blood oxygen", u: "%", lo: 95, hi: 100, d: 0, j: .6, g: "v" },
  { k: "sys", t: "Systolic BP", u: "mmHg", lo: 90, hi: 120, d: 0, j: 3, g: "v" },
  { k: "dia", t: "Diastolic BP", u: "mmHg", lo: 60, hi: 80, d: 0, j: 2, g: "v" },
  { k: "temp", t: "Body temp", u: "°C", lo: 36.1, hi: 37.2, d: 1, j: .1, g: "v" },
  { k: "resp", t: "Respiration", u: "br/min", lo: 12, hi: 20, d: 0, j: 1, g: "v" },
  { k: "rad", t: "Radiation", u: "mSv/day", lo: 0, hi: .8, d: 2, j: .04, g: "s" },
  { k: "bone", t: "Bone loss", u: "%/mo", lo: 0, hi: 2, d: 1, j: .02, g: "s" },
  { k: "muscle", t: "Muscle mass", u: "%", lo: 90, hi: 100, d: 0, j: .3, g: "s" },
  { k: "sleep", t: "Sleep", u: "hours", lo: 7, hi: 9, d: 1, j: .2, g: "s" },
  { k: "stress", t: "Stress index", u: "/100", lo: 0, hi: 40, d: 0, j: 3, g: "s" },
  { k: "o2", t: "Cabin O₂", u: "%", lo: 20, hi: 22, d: 1, j: .1, g: "e" },
  { k: "co2", t: "Cabin CO₂", u: "ppm", lo: 0, hi: 4000, d: 0, j: 150, g: "e" },
  { k: "press", t: "Cabin pressure", u: "kPa", lo: 97, hi: 104, d: 1, j: .3, g: "e" },
  { k: "hum", t: "Humidity", u: "%", lo: 25, hi: 60, d: 0, j: 2, g: "e" }
];
const ADVICE = {
  hr: "Rest and slow breathing; check the heart sensor.", spo2: "Check cabin oxygen partial pressure.",
  sys: "Reduce exertion; re-check blood pressure in 10 min.", dia: "Reduce exertion; re-check blood pressure.",
  temp: "Check cooling loop; watch for infection signs.", resp: "Check air quality and CO₂ scrubbers.",
  rad: "Move to the shielded sleeping quarters.", bone: "Add resistance exercise (ARED) and review calcium.",
  muscle: "Add strength training and protein.", sleep: "Keep a fixed sleep schedule; dim lights at night.",
  stress: "Schedule a relaxation session and a family call.", o2: "Inspect oxygen generator output.",
  co2: "Service CO₂ removal system.", press: "Inspect module hatches and seals.", hum: "Check humidity control."
};
let cur = 0, vals = {}, spike = 0, paused = false, inSAA = false;

const score = (m, v) => {
  if (v >= m.lo && v <= m.hi) return 100;
  const dist = v < m.lo ? m.lo - v : v - m.hi, span = Math.max((m.hi - m.lo) / 2, m.hi * .08, .5);
  return clamp(100 - dist / span * 40, 0, 100);
};
const status = s => s >= 85 ? ["NOMINAL", "ok", "#4dffb0"] : s >= 60 ? ["CAUTION", "warn", "#ffb454"] : ["CRITICAL", "bad", "#ff5d5d"];

function readSensors() { // replace with a real API call
  const b = { ...CAB, ...CREW[cur].b }, o = {};
  M.forEach(m => {
    let v = b[m.k] + (Math.random() - .5) * 2 * m.j;
    if (m.k === "rad" && inSAA) v *= 3;
    if (spike > 0) v += ({ hr: 55, spo2: -7, sys: 30, resp: 9, stress: 35, temp: .9, co2: 2200 })[m.k] || 0;
    o[m.k] = m.k === "spo2" ? Math.min(100, v) : v;
  });
  return o;
}

function render() {
  let total = 0, worst = 100; const al = [], rec = new Set();
  $("cards").innerHTML = M.map(m => {
    const v = vals[m.k], s = score(m, v), st = status(s);
    total += s; worst = Math.min(worst, s);
    if (s < 85) { al.push(`<li class="${st[1]}">${m.t}: ${v.toFixed(m.d)} ${m.u} · ${st[0]}</li>`); rec.add(ADVICE[m.k]); }
    return `<div class="card ${m.g}"><small>${m.t}</small><div class="v">${v.toFixed(m.d)}<em>${m.u}</em></div><div class="bar"><i style="width:${s}%;background:${st[2]}"></i></div></div>`;
  }).join("");
  const sc = Math.round(Math.min(total / M.length, worst + 25)), st = status(sc); // one bad metric can't hide behind the average
  $("score").textContent = sc; $("score").className = "gn " + st[1];
  $("slabel").textContent = st[0]; $("slabel").className = st[1];
  $("arc").style.strokeDashoffset = 314 * (1 - sc / 100); $("arc").style.stroke = st[2];
  $("hrl").textContent = Math.round(vals.hr) + " bpm";
  $("alerts").innerHTML = al.length ? al.join("") : '<li class="ok">All readings nominal.</li>';
  $("recs").innerHTML = rec.size ? [...rec].slice(0, 4).map(r => `<li>${r}</li>`).join("") : "<li>Continue the current routine.</li>";
  crewColor = st[2]; placeCrew();
}

/* ---------- Live ECG ---------- */
const ecg = $("ecg"), ex = ecg.getContext("2d"); let ph = 0, trace = [], lastT = 0, acc = 0;
const beat = p => { const g = (c, w, a) => a * Math.exp(-((p - c) ** 2) / (2 * w * w)); return g(.18, .04, .12) - g(.36, .012, .15) + g(.4, .014, 1) - g(.44, .012, .28) + g(.68, .06, .22); };
function drawECG(now) {
  const [W, H, d] = fit(ecg), hr = vals.hr || 70, dt = Math.min((now - lastT) / 1000 || 0, .1); lastT = now;
  if (!paused) { // one sample per 1/60 s regardless of the screen's refresh rate
    acc += dt;
    while (acc >= 1 / 60) { acc -= 1 / 60; ph += (1 / 60) / (60 / hr); trace.push(beat(ph % 1) + (Math.random() - .5) * .02); }
  }
  const N = Math.floor(W / (2 * d)); while (trace.length > N) trace.shift();
  ex.clearRect(0, 0, W, H); ex.strokeStyle = "rgba(77,216,255,.15)"; ex.lineWidth = 1;
  for (let x = 0; x < W; x += W / 16) { ex.beginPath(); ex.moveTo(x, 0); ex.lineTo(x, H); ex.stroke(); }
  for (let y = 0; y < H; y += H / 4) { ex.beginPath(); ex.moveTo(0, y); ex.lineTo(W, y); ex.stroke(); }
  ex.strokeStyle = hr > 100 || hr < 55 ? "#ff5d5d" : "#4dffb0"; ex.lineWidth = 2 * d; ex.shadowColor = ex.strokeStyle; ex.shadowBlur = 8; ex.beginPath();
  trace.forEach((v, i) => { const x = W - (trace.length - i) * 2 * d, y = H * .72 - v * H * .55; i ? ex.lineTo(x, y) : ex.moveTo(x, y); });
  ex.stroke(); ex.shadowBlur = 0; requestAnimationFrame(drawECG);
}

/* ---------- ISS orbit: live API + simulation ---------- */
const INC = 51.64 * R, PER = 92.68 * 60, OMEGA = 360 / 86164;
const iss = { alt: 420, vel: 27600, vis: "--" };
let live = false, prevLat = null;
function anchorFrom(lat, lon, asc) {
  const M0 = Math.asin(clamp(Math.sin(lat * R) / Math.sin(INC), -1, 1)), m = asc ? M0 : Math.PI - M0;
  return { M: m, s: lon - Math.atan2(Math.cos(INC) * Math.sin(m), Math.cos(m)) / R, t: Date.now() };
}
function at(a, dt) {
  const m = a.M + 2 * Math.PI * dt / PER;
  const lat = Math.asin(Math.sin(INC) * Math.sin(m)) / R, lo = Math.atan2(Math.cos(INC) * Math.sin(m), Math.cos(m)) / R;
  return { lat, lon: wrap180(lo + a.s - OMEGA * dt) };
}
let A = anchorFrom(20, wrap180(Date.now() / 1000), true);
async function poll() {
  if (document.hidden) return; // don't hit the API from a background tab
  try {
    const res = await fetch("https://api.wheretheiss.at/v1/satellites/25544", { signal: AbortSignal.timeout(4000) });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const j = await res.json();
    if (typeof j.latitude !== "number" || typeof j.longitude !== "number") throw new Error("bad payload");
    const asc = prevLat === null || j.latitude === prevLat ? true : j.latitude > prevLat;
    prevLat = j.latitude; A = anchorFrom(j.latitude, j.longitude, asc);
    iss.alt = j.altitude; iss.vel = j.velocity; iss.vis = j.visibility; live = true;
  } catch (e) { live = false; }
  $("feed").textContent = live ? "LIVE" : "SIMULATED"; $("feed").className = live ? "ok" : "warn";
}

/* ---------- World map (dot-matrix) ---------- */
const LAND = [
  [[-168,66],[-156,71],[-125,70],[-95,72],[-82,68],[-65,60],[-55,50],[-67,45],[-76,38],[-81,31],[-80,25],[-90,29],[-97,26],[-97,20],[-88,16],[-83,9],[-78,8],[-85,12],[-93,16],[-105,20],[-110,24],[-115,30],[-122,37],[-125,48],[-135,58],[-150,60],[-165,56]],
  [[-78,8],[-62,10],[-50,0],[-35,-6],[-40,-22],[-48,-28],[-58,-38],[-65,-42],[-68,-52],[-74,-50],[-73,-38],[-71,-18],[-81,-5]],
  [[-55,60],[-45,60],[-20,70],[-20,82],[-60,82],[-70,76]],
  [[-10,36],[-9,43],[-4,48],[5,52],[10,58],[20,70],[40,68],[60,70],[100,77],[140,72],[170,68],[180,65],[160,58],[140,52],[130,43],[122,38],[122,30],[110,20],[105,10],[100,2],[98,15],[90,22],[80,15],[73,20],[67,25],[57,25],[48,30],[35,36],[27,36],[22,38],[12,38],[5,43],[-5,36]],
  [[35,30],[43,13],[52,16],[59,22],[56,26],[48,30]],
  [[-17,21],[-10,35],[10,37],[32,31],[34,28],[43,12],[51,12],[40,-3],[40,-15],[35,-25],[20,-35],[18,-32],[12,-17],[9,-1],[9,4],[-8,4],[-17,14]],
  [[114,-22],[122,-18],[131,-12],[142,-11],[146,-19],[153,-27],[150,-37],[140,-38],[130,-32],[115,-34]],
  [[-5,50],[2,52],[-3,58],[-6,56]], [[130,32],[140,36],[142,45],[138,38]]
];
const inPoly = (x, y, p) => { let c = false; for (let i = 0, j = p.length - 1; i < p.length; j = i++) if ((p[i][1] > y) !== (p[j][1] > y) && x < (p[j][0] - p[i][0]) * (y - p[i][1]) / (p[j][1] - p[i][1]) + p[i][0]) c = !c; return c; };
const DOTS = [];
for (let lo = -180; lo <= 180; lo += 3) for (let la = -85; la <= 85; la += 3) if (la < -70 || LAND.some(p => inPoly(lo, la, p))) DOTS.push([lo, la]);

const cm = $("map"), mx = cm.getContext("2d");
function drawMap(p) {
  const [W, H, d] = fit(cm), X = lo => (lo + 180) / 360 * W, Y = la => (90 - la) / 180 * H, el = (Date.now() - A.t) / 1000;
  mx.clearRect(0, 0, W, H); mx.lineWidth = d; mx.strokeStyle = "rgba(77,216,255,.08)";
  for (let lo = -180; lo <= 180; lo += 30) { mx.beginPath(); mx.moveTo(X(lo), 0); mx.lineTo(X(lo), H); mx.stroke(); }
  for (let la = -60; la <= 60; la += 30) { mx.beginPath(); mx.moveTo(0, Y(la)); mx.lineTo(W, Y(la)); mx.stroke(); }
  mx.fillStyle = "rgba(77,216,255,.42)";
  DOTS.forEach(([lo, la]) => { mx.beginPath(); mx.arc(X(lo), Y(la), 1.1 * d, 0, 7); mx.fill(); });
  mx.save(); mx.setLineDash([5 * d, 4 * d]); mx.strokeStyle = "rgba(255,93,93,.7)"; mx.beginPath(); mx.ellipse(X(-45), Y(-25), 40 / 360 * W, 22 / 180 * H, 0, 0, 7); mx.stroke(); mx.restore();
  [[-2700, 0, "rgba(255,255,255,.3)", []], [0, 5400, "#ffb454", [6 * d, 5 * d]]].forEach(([a, b, c, dash]) => {
    mx.strokeStyle = c; mx.setLineDash(dash); mx.lineWidth = 1.5 * d; mx.beginPath(); let last = null;
    for (let t = a; t <= b; t += 45) { const q = at(A, el + t); (last === null || Math.abs(q.lon - last) > 180) ? mx.moveTo(X(q.lon), Y(q.lat)) : mx.lineTo(X(q.lon), Y(q.lat)); last = q.lon; }
    mx.stroke();
  });
  mx.setLineDash([]); mx.strokeStyle = "rgba(77,216,255,.5)"; mx.beginPath(); mx.ellipse(X(p.lon), Y(p.lat), 20 / 360 * W, 20 / 180 * H, 0, 0, 7); mx.stroke();
  const k = (Date.now() % 2000) / 2000; mx.strokeStyle = `rgba(255,255,255,${1 - k})`; mx.beginPath(); mx.arc(X(p.lon), Y(p.lat), (6 + k * 16) * d, 0, 7); mx.stroke();
  mx.fillStyle = "#fff"; mx.shadowColor = "#4dd8ff"; mx.shadowBlur = 14; mx.beginPath(); mx.arc(X(p.lon), Y(p.lat), 5 * d, 0, 7); mx.fill(); mx.shadowBlur = 0;
  mx.fillStyle = "#4dd8ff"; mx.font = `600 ${12 * d}px Orbitron, sans-serif`; mx.fillText("ISS", X(p.lon) + 10 * d, Y(p.lat) - 8 * d);
}
function frame() {
  const p = at(A, (Date.now() - A.t) / 1000);
  inSAA = ((p.lon + 45) / 40) ** 2 + ((p.lat + 25) / 22) ** 2 < 1;
  $("saa").hidden = !inSAA; drawMap(p);
  $("tel").innerHTML = [["LATITUDE", p.lat.toFixed(3) + "°"], ["LONGITUDE", p.lon.toFixed(3) + "°"], ["ALTITUDE", iss.alt.toFixed(1) + " km"], ["VELOCITY", Math.round(iss.vel).toLocaleString() + " km/h"], ["SUNLIGHT", iss.vis]].map(([a, b]) => `<div><small>${a}</small><b>${b}</b></div>`).join("");
}

/* ---------- Station layout ---------- */
const MODS = [["Zvezda", 85, 100, 50, 16], ["Zarya", 140, 100, 50, 16], ["Unity", 187, 100, 34, 18], ["Destiny Lab", 240, 100, 60, 18], ["Harmony", 292, 100, 34, 18], ["Columbus", 292, 140, 16, 40], ["Kibo", 292, 62, 16, 40], ["Airlock", 187, 134, 16, 34], ["Cupola", 187, 72, 16, 26]];
let crewColor = "#4dd8ff";
$("st").innerHTML = '<line class="tr" x1="240" y1="12" x2="240" y2="188"/>' +
  [[205, 6], [245, 6], [205, 144], [245, 144]].map(([x, y]) => `<rect class="sa" x="${x}" y="${y}" width="30" height="50" rx="2"/>`).join("") +
  MODS.map(([n, x, y, w, h], i) => `<rect class="mod" id="m${i}" x="${x - w / 2}" y="${y - h / 2}" width="${w}" height="${h}" rx="5"/>`).join("") +
  CREW.map((c, i) => `<g class="cd" id="c${i}"><circle r="6"/><text y="2.4">${c.n.split(" ")[1][0]}</text></g>`).join("");
function placeCrew() {
  document.querySelectorAll(".mod").forEach((m, i) => m.classList.toggle("on", CREW.some(c => c.mod === i)));
  CREW.forEach((c, i) => {
    const [, x, y] = MODS[c.mod];
    $("c" + i).style.transform = `translate(${x + (i - 1) * 10}px,${y}px)`;
    $("c" + i).firstChild.setAttribute("fill", i === cur ? crewColor : "#4dd8ff");
  });
  $("loc").innerHTML = CREW.map((c, i) => `<li class="${i === cur ? "sel" : ""}"><i style="background:${i === cur ? crewColor : "#4dd8ff"}"></i>${esc(c.n)}<span>${MODS[c.mod][0]}</span></li>`).join("");
}
setInterval(() => { CREW.forEach(c => c.mod = Math.floor(Math.random() * MODS.length)); placeCrew(); }, 20000);

/* ---------- Controls ---------- */
function tick() { if (paused) return; if (spike > 0) spike--; vals = readSensors(); render(); }
function pick(i) {
  cur = i; spike = 0; trace = []; CREW[i].t0 = CREW[i].t0 || Date.now() - CREW[i].day * 864e5;
  document.querySelectorAll("#tabs button").forEach((b, j) => b.setAttribute("aria-pressed", j === i));
  vals = readSensors(); render();
}
$("tabs").innerHTML = CREW.map(c => `<button aria-pressed="false">${esc(c.n)}</button>`).join("");
document.querySelectorAll("#tabs button").forEach((b, i) => b.onclick = () => pick(i));
$("spike").onclick = () => { if (paused) $("pause").click(); spike = 8; tick(); };
$("reset").onclick = () => pick(cur);
$("pause").onclick = e => { paused = !paused; e.target.setAttribute("aria-pressed", paused); e.target.textContent = paused ? "Resume" : "Pause"; };
setInterval(() => {
  $("utc").textContent = new Date().toISOString().slice(11, 19);
  const s = Math.floor((Date.now() - CREW[cur].t0) / 1000), p = n => String(n).padStart(2, "0");
  $("met").textContent = `MISSION ELAPSED ${Math.floor(s / 86400)}d ${p(Math.floor(s % 86400 / 3600))}:${p(Math.floor(s % 3600 / 60))}:${p(s % 60)}`;
}, 1000);

pick(0); poll(); setInterval(poll, 5000); setInterval(tick, 2000); setInterval(frame, 500); frame(); requestAnimationFrame(drawECG);
