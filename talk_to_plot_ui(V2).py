from __future__ import annotations
import base64, io, os, sys, threading, importlib.util
from pathlib import Path
import webview
HTML_CONTENT = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VoiceScript — UI Preview</title>
<style>
:root {
    --ink:#202124;
    --muted:#73767c;
    --paper:#f5f5f7;
    --card:#fff;
    --line:#e5e5e9;
    --green:#087e68;
    --green2:#e8f4f0;
    --amber:#a66c16;
    --red:#bd3b32;
    --shadow:0 1px 3px #0000000a,0 5px 16px #00000008
}
 * {
    box-sizing:border-box
}
body {
    margin:0;
    background:var(--paper);
    color:var(--ink);
    font:13px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif
}
.shell {
    max-width:1120px;
    margin:auto;
    padding:16px 22px 26px
}
.top {
    display:flex;
    align-items:center;
    justify-content:space-between;
    border-bottom:1px solid var(--line);
    padding-bottom:12px
}
.brand {
    display:flex;
    align-items:center;
    gap:9px
}
.logo {
    width:32px;
    height:32px;
    background:var(--green);
    border-radius:9px;
    color:white;
    display:grid;
    place-items:center
}
.logo svg {
    width:24px;
    height:24px
}
.brand h1 {
    font-size:16px;
    letter-spacing:-.25px;
    margin:0
}
.brand p {
    margin:1px 0 0;
    color:var(--muted);
    font-size:11px
}
.pill {
    display:flex;
    align-items:center;
    gap:7px;
    border:1px solid var(--line);
    border-radius:99px;
    padding:6px 10px;
    background:#fff;
    font-size:11px;
    color:#62656b
}
.dot {
    width:7px;
    height:7px;
    background:#bd8a3b;
    border-radius:50%
}
.hero {
    display:flex;
    justify-content:space-between;
    align-items:end;
    margin:10px 0 14px;
    min-height:8px
}
.hero-right {
    font:10px ui-monospace,monospace;
    color:#868990
}
.grid {
    display:grid;
    grid-template-columns:minmax(340px,.92fr) minmax(0,1.08fr);
    gap:12px
}
.column-title {
    font-size:11px;
    text-transform:uppercase;
    letter-spacing:.8px;
    color:#777a80;
    font-weight:700;
    padding:0 2px;
    margin:0 0 -4px
}
.left,.right {
    display:flex;
    flex-direction:column;
    gap:12px
}
.card {
    background:var(--card);
    border:1px solid var(--line);
    border-radius:12px;
    box-shadow:var(--shadow);
    padding:15px
}
.cardhead {
    display:flex;
    align-items:flex-start;
    justify-content:space-between;
    margin-bottom:12px
}
.cardhead h3 {
    margin:0;
    font-size:13px;
    letter-spacing:-.1px
}
.cardhead p {
    margin:3px 0 0;
    font-size:11px;
    color:var(--muted)
}
.step {
    font:10px ui-monospace,monospace;
    color:#999ba1
}
.connectrow {
    display:grid;
    grid-template-columns:1fr 1fr auto;
    gap:8px;
    align-items:end
}
.field label {
    display:block;
    font-size:10px;
    color:var(--muted);
    margin:0 0 4px
}
.select,.input {
    height:33px;
    width:100%;
    border:1px solid #d9d9de;
    background:#fff;
    border-radius:7px;
    padding:0 9px;
    color:var(--ink);
    font:12px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif
}
.btn {
    border:0;
    border-radius:7px;
    padding:9px 12px;
    font:600 11px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    cursor:default;
    white-space:nowrap
}
.primary {
    color:#fff;
    background:var(--green)
}
.secondary {
    background:#f5f5f7;
    color:#36383d;
    border:1px solid #e1e1e5
}
.danger {
    background:#fff1ef;
    color:var(--red);
    border:1px solid #f0d7d3
}
.connect {
    height:33px
}
.substatus {
    display:flex;
    justify-content:space-between;
    margin-top:10px;
    padding-top:9px;
    border-top:1px solid #f0f0f2;
    color:var(--muted);
    font-size:10px
}
.substatus strong {
    color:var(--amber);
    font-weight:600
}
.write-layout {
    display:grid;
    grid-template-columns:1fr 164px;
    gap:12px
}
.bigmic {
    height:102px;
    border-radius:10px;
    background:var(--green2);
    display:grid;
    place-items:center;
    text-align:center;
    color:var(--green)
}
.micicon {
    font-size:23px
}
.bigmic b {
    display:block;
    font-size:12px;
    margin-top:3px
}
.bigmic small {
    display:block;
    color:#718273;
    font-size:10px;
    margin-top:2px
}
.bigmic .click-record {
    font-size:11px;
    font-weight:600;
    color:#718273;
    margin-top:7px
}
.review {
    grid-column:1/-1;
    border:1px solid var(--line);
    border-radius:8px;
    background:#fafafd;
    padding:10px 11px;
    min-height:55px
}
.review label {
    color:var(--muted);
    font-size:9px;
    text-transform:uppercase;
    letter-spacing:.7px
}
.review p {
    margin:4px 0 0;
    font-size:12px;
    color:#8b8d94
}
.actionstack {
    display:flex;
    flex-direction:column;
    gap:6px
}
.actionstack .btn {
    height:31px;
    padding:7px
}
.statusbar {
    margin-top:10px;
    background:#f5f5f7;
    border-radius:7px;
    padding:7px 9px;
    color:#656970;
    font-size:10px;
    display:flex;
    gap:7px;
    align-items:center
}
.statusbar .dot {
    background:#68a68c
}
.smallgrid {
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:8px
}
.smallgrid .input {
    height:29px;
    font:11px ui-monospace,monospace
}
.smallgrid label {
    font-size:9px
}
.tools {
    display:flex;
    gap:6px;
    margin-top:11px;
    padding-top:10px;
    border-top:1px solid #f0f0f2
}
.tools .btn {
    flex:1;
    padding:7px 4px;
    font-size:10px
}
.photo {
    height:166px;
    border:1px dashed #d6d7dc;
    border-radius:9px;
    background:#f8f8fa;
    display:grid;
    place-items:center;
    position:relative;
    overflow:hidden
}
.photo svg {
    width:88%;
    height:90%
}
.photo img.actual-preview {
    max-width:96%;
    max-height:96%;
    object-fit:contain
}
.image-meta {
    display:flex;
    align-items:center;
    justify-content:space-between;
    margin:10px 0
}
.file {
    font-size:11px;
    font-weight:600
}
.file small {
    display:block;
    color:var(--muted);
    font-weight:400;
    margin-top:1px;
    font-size:10px
}
.dims {
    display:flex;
    gap:6px
}
.dims .input {
    width:62px;
    height:28px;
    font:10px ui-monospace,monospace
}
.auto-dimensions {
    display:flex;
    flex-direction:column;
    align-items:flex-end;
    gap:2px
}
.auto-dimensions strong {
    font-size:11px;
    color:var(--ink)
}
.dims span {
    font-size:9px;
    color:var(--muted);
    align-self:center
}
.image-actions {
    display:flex;
    gap:7px
}
.image-actions .btn {
    flex:1
}
.settings {
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:12px
}
.settings .card {
    padding:13px
}
.setting-row {
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin:8px 0;
    font-size:11px;
    color:#5e6067
}
.setting-row .input {
    width:76px;
    text-align:right;
    height:27px;
    font:10px ui-monospace,monospace
}
.footer {
    color:#999ba1;
    text-align:center;
    font-size:9px;
    margin-top:14px
}
.previewtag {
    border:1px solid #e6dcc9;
    color:#8f6b37;
    background:#fbf6eb;
    border-radius:5px;
    padding:3px 6px;
    font-size:9px;
    font-weight:600;
    text-transform:uppercase;
    letter-spacing:.4px
}
 @media(max-width:760px) {
    .shell {
        padding:13px
    }
.grid {
        grid-template-columns:1fr
    }
.hero-right {
        display:none
    }

}
@media(max-width:520px) {
    .connectrow {
        grid-template-columns:1fr 1fr
    }
.connect {
        grid-column:1/-1
    }
.write-layout {
        grid-template-columns:1fr
    }
.actionstack {
        display:grid;
        grid-template-columns:1fr 1fr
    }
.review {
        grid-column:auto
    }
.smallgrid {
        grid-template-columns:1fr 1fr
    }
.settings {
        grid-template-columns:1fr
    }

}
  /* Roomier reading and control spacing */ body {
    font-size:14px;
    line-height:1.5
}
 .shell {
    max-width:1240px;
    padding:22px 28px 34px
}
 .grid {
    gap:18px
}
 .left,.right {
    gap:16px
}
 .card {
    padding:20px;
    border-radius:14px
}
 .cardhead {
    margin-bottom:16px
}
 .cardhead h3 {
    font-size:15px
}
 .cardhead p {
    font-size:12px;
    line-height:1.55;
    margin-top:5px
}
 .step {
    font-size:11px
}
 .connectrow {
    gap:12px
}
 .field label {
    font-size:11px;
    margin-bottom:6px
}
 .select,.input {
    height:38px;
    padding:0 11px;
    font-size:13px
}
 .btn {
    padding:11px 14px;
    font-size:12px
}
 .connect {
    height:38px
}
 .substatus {
    margin-top:14px;
    padding-top:12px;
    font-size:11px
}
 .write-layout {
    grid-template-columns:minmax(0,1fr) 180px;
    gap:16px
}
 .bigmic {
    height:124px
}
 .bigmic b {
    font-size:14px
}
.bigmic .click-record {
    font-size:12px
}
 .review {
    padding:13px 14px;
    min-height:66px
}
.review label {
    font-size:10px
}
.review textarea {
    font-size:13px!important;
    line-height:1.5
}
 .actionstack {
    gap:9px
}
.actionstack .btn {
    height:38px;
    padding:9px
}
 .statusbar {
    margin-top:14px;
    padding:10px 12px;
    font-size:11px;
    line-height:1.5
}
 .smallgrid {
    gap:11px
}
.smallgrid .input {
    height:34px
}
.smallgrid label {
    font-size:10px
}
 .tools {
    gap:9px;
    margin-top:15px;
    padding-top:13px
}
.tools .btn {
    padding:9px 6px;
    font-size:11px
}
 .photo {
    height:194px
}
 .image-meta {
    margin:13px 0
}
.file {
    font-size:12px
}
.file small {
    font-size:11px
}
 .dims .input {
    height:32px
}
 .settings {
    gap:12px
}
.setting-row {
    font-size:12px;
    margin:10px 0
}
.setting-row .input {
    height:31px;
    font-size:11px
}
 @media(max-width:760px) {
    .shell {
        padding:16px
    }
.grid {
        gap:14px
    }
.card {
        padding:16px
    }

}
  /* More breathing room between settings and actions */ body {
    font-size:14px;
    line-height:1.55
}
 .shell {
    max-width:1320px;
    padding:26px 32px 40px
}
 .grid {
    gap:24px
}
 .left,.right {
    gap:22px
}
 .column-title {
    font-size:12px;
    margin-bottom:0
}
 .card {
    padding:24px;
    border-radius:16px
}
 .cardhead {
    margin-bottom:20px
}
 .cardhead h3 {
    font-size:16px
}
 .cardhead p {
    font-size:13px;
    line-height:1.6;
    margin-top:6px
}
 .connectrow {
    gap:14px
}
 .field label {
    font-size:12px;
    margin-bottom:8px
}
 .select,.input {
    height:42px;
    padding:0 12px;
    font-size:14px
}
 .btn {
    padding:12px 16px;
    font-size:13px
}
 .connect {
    height:42px
}
 .substatus {
    margin-top:18px;
    padding-top:14px;
    font-size:12px
}
 .smallgrid {
    gap:15px 18px
}
 .smallgrid .input {
    height:38px;
    font-size:13px
}
 .smallgrid label {
    font-size:11px
}
 .settings {
    gap:22px
}
 .setting-row {
    font-size:13px;
    margin:15px 0;
    gap:12px
}
 .setting-row .input {
    width:92px;
    height:36px;
    font-size:12px
}
 .tools {
    gap:12px;
    margin-top:18px;
    padding-top:16px
}
 .tools .btn {
    padding:11px 8px;
    font-size:12px
}
 .write-layout {
    grid-template-columns:minmax(0,1fr) 190px;
    gap:18px
}
 .bigmic {
    height:144px
}
 .bigmic b {
    font-size:15px
}
.bigmic .click-record {
    font-size:13px
}
 .actionstack {
    gap:11px
}
.actionstack .btn {
    height:42px;
    padding:10px
}
 .review {
    padding:16px;
    min-height:76px
}
.review label {
    font-size:11px
}
.review textarea {
    font-size:14px!important;
    line-height:1.6
}
 .statusbar {
    margin-top:17px;
    padding:12px 14px;
    font-size:12px
}
 .photo {
    height:220px
}
 .image-meta {
    margin:17px 0
}
.file {
    font-size:13px
}
.file small {
    font-size:12px
}
 .dims .input {
    height:36px
}
.auto-dimensions strong {
    font-size:13px
}
 @media(max-width:900px) {
    .shell {
        padding:18px
    }
.grid {
        gap:16px
    }
.left,.right {
        gap:16px
    }
.card {
        padding:18px
    }

}
</style>
</head>
<body>
<main class="shell">
<header class="top">
<div class="brand">
<div class="logo" aria-label="A drawn in ink">
<svg viewBox="0 0 32 32" role="img" aria-label="A">
<path d="M7 25 14.2 7.5c.7-1.7 3-1.7 3.7 0L25 25M10 18h12" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M10 18h12" fill="none" stroke="#d8f0e9" stroke-width=".8" stroke-linecap="round"/>
</svg>
</div>
<div>
<h1>VoiceScript</h1>
<p>Speech to pen plotter</p>
</div>
</div>
<div class="pill">
<i class="dot">
</i> Machine disconnected</div>
</header>
<section class="hero">
<div>
</div>
<div class="hero-right">MARLIN · 115200 BAUD</div>
</section>
<div class="grid">
<div class="left">
<h2 class="column-title">Set up</h2>
<section class="card">
<div class="cardhead">
<div>
<h3>Machine connection</h3>
</div>
<span class="step">01</span>
</div>
<div class="connectrow">
<div class="field">
<label>Firmware</label>
<select class="select" id="firmware">
<option>MARLIN</option>
<option>GRBL</option>
</select>
</div>
<div class="field">
<label>Baud rate</label>
<select class="select" id="baud">
<option>115200</option>
<option>250000</option>
</select>
</div>
<button class="btn primary connect" id="connect">Connect machine&nbsp; →</button>
</div>
<div class="substatus">
<span>Connection status</span>
<strong id="connection-status">Waiting for machine</strong>
</div>
</section>
<section class="card">
<div class="cardhead">
<div>
<h3>Writing setup</h3>
</div>
<span class="step">02</span>
</div>
<div class="smallgrid">
<div class="field">
<label>Font size (mm)</label>
<input class="input" data-setting="FONT_SIZE" value="13.0">
</div>
<div class="field">
<label>Line spacing (mm)</label>
<input class="input" data-setting="LINE_SPACING" value="20.0">
</div>
<div class="field">
<label>Start X (mm)</label>
<input class="input" data-setting="START_X" value="15.0">
</div>
<div class="field">
<label>Start Y (mm)</label>
<input class="input" data-setting="START_Y" value="60.0">
</div>
<div class="field">
<label>Machine width (mm)</label>
<input class="input" data-setting="MAX_X" value="200.0">
</div>
<div class="field">
<label>Machine length (Y-axis, mm)</label>
<input class="input" data-setting="MACHINE_HEIGHT" value="60.0">
</div>
</div>
</section>
<section class="card">
<div class="cardhead">
<div>
<h3>Movement & pen height</h3>
</div>
<span class="step">03</span>
</div>
<div class="settings">
<div>
<div class="setting-row">Drawing speed (mm/min) <input class="input" data-setting="DRAW_FEED_RATE" value="2800">
</div>
<div class="setting-row">Travel speed (mm/min) <input class="input" data-setting="TRAVEL_FEED_RATE" value="6500">
</div>
<div class="setting-row">Z speed (mm/min) <input class="input" data-setting="Z_FEED_RATE" value="600">
</div>
</div>
<div>
<div class="setting-row">Pen down (mm) <input class="input" data-setting="PEN_DOWN_Z" value="0.7">
</div>
<div class="setting-row">Pen up (mm) <input class="input" data-setting="PEN_UP_Z" value="3.5">
</div>
<div class="setting-row">Word spacing (mm) <input class="input" data-setting="WORD_SPACING" value="3.9">
</div>
</div>
</div>
<div class="tools">
<button class="btn secondary" data-jog="home">⌂ &nbsp;Home</button>
<button class="btn secondary" data-jog="up">↑ &nbsp;Pen up</button>
<button class="btn secondary" data-jog="down">↓ &nbsp;Pen down</button>
</div>
</section>
<div class="tools">
<button class="btn secondary" id="apply-settings">Apply settings</button>
<button class="btn secondary" id="save-settings">Save settings</button>
<button class="btn secondary" id="load-settings">Load settings</button>
</div>
</div>
<div class="right">
<h2 class="column-title">Create</h2>
<section class="card">
<div class="cardhead">
<div>
<h3>Speak to write</h3>
<p>Record, review, then write.</p>
</div>
<span class="step">01 / TEXT</span>
</div>
<div class="write-layout">
<div class="bigmic">
<div>
<div class="micicon">◉</div>
<b>Ready to listen</b>
<div class="click-record">Click to record</div>
</div>
</div>
<div class="actionstack">
<button class="btn primary" id="speak">◉ &nbsp;Speak & Review</button>
<button class="btn secondary" id="retalk">↻ &nbsp;Try again</button>
<button class="btn danger" id="stop">■ &nbsp;Stop / cancel</button>
</div>
<div class="review">
<label>Recognized words · review before writing</label>
<textarea id="recognized" aria-label="Recognized words" placeholder="Your transcription will appear here…" style="width:100%;min-height:42px;resize:vertical;border:0;background:transparent;color:var(--ink);font:12px -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;outline:none">
</textarea>
</div>
</div>
<div class="statusbar">
<i class="dot">
</i>
<span class="live-status">Connect a machine to enable voice writing.</span>
</div>
</section>
<section class="card">
<div class="cardhead">
<div>
<h3>Draw an image</h3>
<p>Convert image edges into a plotter path.</p>
</div>
<span class="step">02 / IMAGE</span>
</div>
<div class="photo">
<svg viewBox="0 0 460 230" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M34 190h392M67 190V62h326v128M70 151l76-63 52 45 63-70 131 99M134 119a20 20 0 1 0 0-40 20 20 0 0 0 0 40Z" stroke="#82917e" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M91 173c30-22 41-25 66-4 20 17 37 15 58-3 23-20 39-25 61-7 29 23 44 16 65-2 19-17 37-18 62 2" stroke="#b2b9aa" stroke-width="1.6" stroke-dasharray="4 5"/>
<circle cx="146" cy="99" r="2.5" fill="#82917e"/>
<text x="230" y="218" text-anchor="middle" fill="#888b80" font-size="10" font-family="sans-serif" letter-spacing="1.4">OUTLINE PREVIEW</text>
</svg>
</div>
<div class="image-meta">
<div class="file" id="image-name">No image selected<small>Choose a PNG or JPEG image</small>
</div>
<div class="dims auto-dimensions">
<span>Auto fit</span>
<strong id="image-size">— × — mm</strong>
</div>
</div>
<div class="image-actions">
<button class="btn secondary" id="choose-image">Choose image</button>
<button class="btn primary" id="print-image">Print image&nbsp; →</button>
</div>
<div class="statusbar">
<i class="dot">
</i>
<span id="image-status">Choose an image to begin.</span>
</div>
</section>
</div>
</main>
<script>
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
    
const setStatus=t=>{$$('.live-status').forEach(e=>e.textContent=t)}
;
    
let settingsRestored=false;
    
async function restoreSavedSettings(){
 if(!window.pywebview?.api){setTimeout(restoreSavedSettings,250);
    return}

 if(settingsRestored)return;
    settingsRestored=true;
    
 try{const v=JSON.parse(localStorage.getItem('voicescript-ui2-settings')||'null');
    if(!v)return;
    
 $('#firmware').value=v.FIRMWARE||$('#firmware').value;
    $('#baud').value=v.BAUD_RATE||$('#baud').value;
    
 $$('[data-setting]').forEach(e=>{const k=e.dataset.setting;
    if(k==='MACHINE_HEIGHT')e.value=v.MACHINE_HEIGHT??(Number(v.START_Y)-Number(v.MIN_Y));
    else if(v[k]!==undefined)e.value=v[k]}
);
    
 await call('apply_settings',settings());
    setStatus('Saved settings loaded');
    }
catch(e){setStatus('Saved settings could not be loaded: '+e)}

}


const call=async(name,...args)=>{try{const r=await window.pywebview.api[name](...args);
    if(r&&r.status)setStatus(r.status);
    return r}
catch(e){setStatus(String(e));
    return {ok:false}
}
}
;
    
function settings(){const v={FIRMWARE:$('#firmware').value,BAUD_RATE:$('#baud').value,WORD_END_PADDING:'2.6'}
;
    $$('[data-setting]').forEach(e=>v[e.dataset.setting]=e.value);
    v.MIN_Y=Number(v.START_Y)-Number(v.MACHINE_HEIGHT);
    return v}

async function poll(){if(!window.pywebview?.api){setTimeout(poll,250);
    return}
try{const s=await window.pywebview.api.get_state();
    setStatus(s.status);
    const r=$('#recognized');
    if(s.recognized && r.value!==s.recognized)r.value=s.recognized;
    const pill=$('.pill');
    pill.innerHTML=`<i class="dot" style="background:${s.connected?'#68a68c':'#bd8a3b'}">
</i> ${s.connected?'Machine connected':'Machine disconnected'}`;
    $('#connection-status').textContent=s.connection_status|| (s.connected?'Connected':'Waiting for machine');
    $('#speak').textContent=s.recognized?'✓  Confirm & write':'◉  Speak & Review';
    $('#speak').disabled=!!s.busy;
    $('#stop').disabled=!s.busy;
    if(s.image)$('#image-name').innerHTML=`${s.image}<small>${s.image_ready?'Plot path ready':'Image selected'}</small>`;
    if(s.image_width)$('#image-size').textContent=`${s.image_width} × ${s.image_height} mm`;
    $('#image-status').textContent=s.image_status||s.status}
catch(e){}
setTimeout(poll,500)}

window.addEventListener('pywebviewready',()=>{restoreSavedSettings();
    poll()}
);
    setTimeout(()=>{restoreSavedSettings();
    poll()}
,250);
    
$('#connect').onclick=async()=>{await call('apply_settings',settings());
    await call('connect',$('#firmware').value,$('#baud').value)}
;
    
$('#speak').onclick=async()=>{const state=await window.pywebview.api.get_state();
    if(!state.connected){alert('Connect the machine before writing.');
    return}
const t=$('#recognized').value.trim();
    if(t)await call('write_text',t);
    else await call('listen')}
;
    $('#retalk').onclick=async()=>{const state=await window.pywebview.api.get_state();
    if(!state.connected){alert('Connect the machine before recording text to write.');
    return}
$('#recognized').value='';
    call('listen')}
;
    $('#stop').onclick=()=>call('stop');
    
$('#choose-image').onclick=async()=>{await call('apply_settings',settings());
    const r=await call('choose_image');
    if(r?.ok){if(r.preview){const photo=$('.photo');
    photo.innerHTML=`<img class="actual-preview" alt="Detected image outline" src="data:image/png;base64,${r.preview}">`}
$('#image-size').textContent=`${r.width} × ${r.height} mm`;
    const prep=await call('prepare_image');
    $('#image-status').textContent=prep.status}
}
;
    
$('#print-image').onclick=async()=>{const state=await window.pywebview.api.get_state();
    if(!state.connected){alert('Connect the machine before printing an image.');
    return}
await call('apply_settings',settings());
    const prep=await call('prepare_image');
    if(prep?.ok&&confirm('The plotter will move and draw this image. Continue?'))await call('print_image')}
;
    
$('#apply-settings').onclick=()=>call('apply_settings',settings());
    $('#save-settings').onclick=async()=>{const v=settings();
    localStorage.setItem('voicescript-ui2-settings',JSON.stringify(v));
    await call('apply_settings',v);
    setStatus('Settings saved')}
;
    $('#load-settings').onclick=async()=>{const v=JSON.parse(localStorage.getItem('voicescript-ui2-settings')||'null');
    if(!v){setStatus('No saved settings');
    return}
$('#firmware').value=v.FIRMWARE;
    $('#baud').value=v.BAUD_RATE;
    $$('[data-setting]').forEach(e=>e.value=v[e.dataset.setting]??e.value);
    await call('apply_settings',v)}
;
    $$('[data-jog]').forEach(b=>b.onclick=()=>call('jog',b.dataset.jog));
</script>
</body>
</html>
"""
HERE = Path(__file__).resolve().parent
CORE_FILE = Path(getattr(sys, '_MEIPASS', HERE)) / 'talk_to_plot V2.1.py'
if not CORE_FILE.exists():
    CORE_FILE = HERE / 'talk_to_plot V2.1.py'
if not CORE_FILE.exists():
    raise SystemExit(f'Could not find VoiceScript backend: {CORE_FILE}')
spec = importlib.util.spec_from_file_location('voicescript_v3_backend', CORE_FILE)
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)
core = backend.__dict__
controller = backend.VoiceScriptController()
core['machine_device'] = None
lock = threading.RLock()
state = {'status': 'Not connected', 'connection_status': 'Waiting for machine', 'connected': False, 'busy': False, 'recognized': '', 'image': '', 'image_width': None, 'image_height': None, 'image_status': 'Choose an image to begin.', 'image_ready': False}
window = None

class Bridge:

    def get_state(self):
        with lock:
            return dict(state)

    def apply_settings(self, v):
        try:
            for k in ('FONT_SIZE', 'START_X', 'START_Y', 'MAX_X', 'LINE_SPACING', 'DRAW_FEED_RATE', 'TRAVEL_FEED_RATE', 'Z_FEED_RATE', 'PEN_DOWN_Z', 'PEN_UP_Z', 'WORD_SPACING', 'WORD_END_PADDING'):
                core[k] = float(v[k])
            if 'MACHINE_HEIGHT' in v:
                core['set_machine_dimensions'](v['MAX_X'], v['MACHINE_HEIGHT'])
            else:
                core['MIN_Y'] = float(v['MIN_Y'])
            core['FIRMWARE'] = str(v['FIRMWARE']).upper()
            core['BAUD_RATE'] = int(v['BAUD_RATE'])
            if core.get('selected_image_path'):
                width, height = controller.fit_image_size(core['selected_image_path'])
                with lock:
                    state.update(image_width=width, image_height=height)
            with lock:
                state['status'] = 'Settings applied'
            return {'ok': True, 'status': 'Settings applied'}
        except Exception as e:
            return {'ok': False, 'status': f'Check settings: {e}'}

    def connect(self, firmware, baud):
        with lock:
            if state['busy']:
                return {'ok': False, 'status': 'Machine is busy'}
            if state['connected']:
                return {'ok': True, 'status': 'Already connected'}
            state.update(busy=True, status='Searching for machine…', connection_status='Searching for machine…')

        def work():
            try:
                dev = controller.connect(firmware=firmware, baud_rate=baud)
                core['machine_device'] = dev
                error = controller.last_connection_error
                with lock:
                    state.update(connected=bool(dev), status='Connected' if dev else error or 'Connection failed', connection_status='Connected' if dev else error or 'Connection failed')
            except Exception as e:
                with lock:
                    state.update(connected=False, status=f'Connection failed: {e}', connection_status=f'Connection failed: {e}')
            finally:
                with lock:
                    state['busy'] = False
        threading.Thread(target=work, daemon=True).start()
        return {'ok': True, 'status': 'Searching for machine…'}

    def listen(self):
        with lock:
            if not state['connected']:
                return {'ok': False, 'status': 'Connect the machine first'}
            if state['busy']:
                return {'ok': False, 'status': 'An operation is already running'}
            state.update(busy=True, recognized='', status='Listening…')

        def work():
            try:
                text = core['listen_for_text']()
                with lock:
                    state.update(recognized=text, status='Review the recognized words, then confirm to write.')
            except Exception as e:
                with lock:
                    state['status'] = f'Listening failed: {e}'
            finally:
                with lock:
                    state['busy'] = False
        threading.Thread(target=work, daemon=True).start()
        return {'ok': True, 'status': 'Listening…'}

    def write_text(self, text):
        dev = core.get('machine_device')
        with lock:
            if not state['connected'] or not controller.connected:
                message = 'Connect the machine before writing text.'
                state['status'] = message
                return {'ok': False, 'warning': True, 'status': message}
            if state['busy']:
                return {'ok': False, 'status': 'An operation is already running'}
            state.update(busy=True, status='Writing…')
            core['cancel_requested'].clear()

        def cb(msg):
            with lock:
                state['status'] = msg

        def work():
            try:
                ok = core['write_text'](dev, str(text).strip(), cb)
                with lock:
                    if ok:
                        state['status'] = 'Writing finished'
                    state['recognized'] = ''
            except Exception as e:
                with lock:
                    state['status'] = f'Writing failed: {e}'
            finally:
                with lock:
                    state['busy'] = False
        threading.Thread(target=work, daemon=True).start()
        return {'ok': True, 'status': 'Writing…'}

    def stop(self):
        core['cancel_requested'].set()
        dev = core.get('machine_device')
        try:
            if dev and dev.is_open:
                dev.write(b'M410\n' if str(core['FIRMWARE']).upper() == 'MARLIN' else b'!')
                dev.flush()
        except Exception:
            pass
        with lock:
            state['status'] = 'STOP requested — check the machine.'
        return {'ok': True, 'status': state['status']}

    def choose_image(self):
        try:
            result = window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=False, file_types=('Image files (*.png;*.jpg;*.jpeg)', 'All files (*.*)'))
            if not result:
                return {'ok': False, 'status': 'No image selected'}
            path = result[0] if isinstance(result, (tuple, list)) else result
            from PIL import Image
            with Image.open(path) as image:
                image.verify()
            core['selected_image_path'] = path
            core['image_gcode_commands'] = []
            edges = core['get_image_edges'](path, 'Could not open the image for preview.')
            Image = core['Image']
            preview = Image.fromarray(255 - edges).convert('RGB')
            preview.thumbnail((700, 440))
            buf = io.BytesIO()
            preview.save(buf, format='PNG')
            width, height = controller.fit_image_size(path)
            with lock:
                state.update(image=os.path.basename(path), image_width=width, image_height=height, image_ready=False, image_status='Image selected — generating plot path…', status='Image selected')
            return {'ok': True, 'status': 'Image selected', 'width': width, 'height': height, 'preview': base64.b64encode(buf.getvalue()).decode('ascii')}
        except Exception as e:
            with lock:
                state.update(image_status=f'Image error: {e}', status=f'Image error: {e}')
            return {'ok': False, 'status': str(e)}

    def prepare_image(self):
        path = core.get('selected_image_path')
        if not path:
            return {'ok': False, 'status': 'Choose an image first'}
        try:
            commands = controller.make_image_gcode(path)
            core['image_gcode_commands'] = commands
            width, height = controller.fit_image_size(path)
            with lock:
                state.update(image_width=width, image_height=height, image_ready=True, image_status='G-code ready — review before printing.', status='G-code ready — review before printing.')
            return {'ok': True, 'status': 'G-code ready — review before printing.'}
        except Exception as e:
            with lock:
                state.update(image_ready=False, image_status=f'Image setup failed: {e}', status=f'Image setup failed: {e}')
            return {'ok': False, 'status': str(e)}

    def print_image(self):
        dev = core.get('machine_device')
        commands = list(core.get('image_gcode_commands', []))
        with lock:
            if not state['connected'] or not controller.connected:
                message = 'Connect the machine before printing an image.'
                state.update(status=message, image_status=message)
                return {'ok': False, 'warning': True, 'status': message}
            if state['busy']:
                return {'ok': False, 'status': 'Machine is busy'}
            if not commands:
                return {'ok': False, 'status': 'Choose an image and prepare its path first'}
            state.update(busy=True, status='Printing image…')
            core['cancel_requested'].clear()

        def work():
            success = True
            try:
                seq = ['G21', 'G90', f"G0 Z{core['PEN_UP_Z']:.2f} F{core['Z_FEED_RATE']}"] + commands
                for i, cmd in enumerate(seq):
                    if core['cancel_requested'].is_set() or not core['send_gcode_line'](dev, cmd):
                        success = False
                        break
                    if i % 80 == 0:
                        with lock:
                            state['status'] = f'Printing image… ({i}/{len(seq)} commands)'
                if success and (not core['cancel_requested'].is_set()):
                    success = core['send_gcode_line'](dev, core['get_home_command']())
            except Exception as e:
                with lock:
                    state['status'] = f'Printing failed: {e}'
                success = False
            finally:
                with lock:
                    if core['cancel_requested'].is_set():
                        state['status'] = 'Image printing cancelled — check the machine.'
                    elif success:
                        state['status'] = 'Image printing finished'
                    elif not state['status'].startswith('Printing failed:'):
                        state['status'] = 'Printing failed'
                    state['busy'] = False
        threading.Thread(target=work, daemon=True).start()
        return {'ok': True, 'status': 'Printing image…'}

    def jog(self, action):
        dev = core.get('machine_device')
        if not dev:
            return {'ok': False, 'status': 'Connect the machine first'}
        cmds = {'home': core['get_home_command'](), 'up': f"G0 Z{core['PEN_UP_Z']:.2f} F{core['Z_FEED_RATE']}", 'down': f"G1 Z{core['PEN_DOWN_Z']:.2f} F{core['Z_FEED_RATE']}"}
        if action not in cmds:
            return {'ok': False, 'status': 'Unknown machine command'}

        def work():
            ok = core['send_gcode_line'](dev, cmds[action])
            msg = ('Machine homed' if action == 'home' else 'Pen raised' if action == 'up' else 'Pen lowered') if ok else 'Machine did not accept command'
            with lock:
                state['status'] = msg
        threading.Thread(target=work, daemon=True).start()
        return {'ok': True, 'status': 'Command sent'}

    def close(self):
        dev = core.get('machine_device')
        try:
            if dev:
                core['send_gcode_line'](dev, f"G0 Z{core['PEN_UP_Z']:.2f} F{core['Z_FEED_RATE']}")
                dev.close()
        except Exception:
            pass
        return True
bridge = Bridge()
window = webview.create_window('VoiceScript · UI 2', html=HTML_CONTENT, js_api=bridge, width=1320, height=930, min_size=(900, 700))
window.events.closing += bridge.close
webview.start()
