let patients = [], selectedId = null;
let chHR=null, chTemp=null, chBP=null;

const $ = id => document.getElementById(id);

function tickClock(){ $('clock').textContent = new Date().toUTCString(); }
setInterval(tickClock, 1000); tickClock();

function statusOf(v){
  const bad = (v.heart_rate<50||v.heart_rate>120)||v.spo2<92||v.temperature>38||v.temperature<35||v.bp_systolic>180||v.bp_systolic<80;
  return bad;
}

async function loadStats(){
  const r = await fetch('/api/stats'); const s = await r.json();
  $('stPatients').textContent=s.patients; $('stDevices').textContent=s.devices;
  $('stReadings').textContent=s.readings; $('stAlerts').textContent=s.alerts;
}
async function loadAlerts(){
  const r = await fetch('/api/alerts'); const a = await r.json();
  $('alertList').innerHTML = a.length ? '' : '<p class="muted">No alerts. All vitals normal.</p>';
  a.forEach(x=>{
    const d=document.createElement('div'); d.className='alert-item';
    d.innerHTML=`<b>${x.patient_name}</b> <small>(${x.device_id})</small><br/>${x.alerts.join(' • ')}`;
    $('alertList').appendChild(d);
  });
}
async function loadPatients(){
  const r = await fetch('/api/patients'); patients = await r.json();
  const box=$('patientList'); box.innerHTML='';
  if(!selectedId && patients.length) selectedId=patients[0].id;
  patients.forEach(p=>{
    const b=document.createElement('button');
    b.className='pat'+(p.id===selectedId?' active':'');
    const bad=p.alerts&&p.alerts.length>0;
    const latest=p.latest?`${p.latest.heart_rate} bpm • ${p.latest.spo2}% SpO₂`:'no data';
    b.innerHTML=`<b>${p.name}</b><span class="badge ${bad?'bad':''}">${bad?'ALERT':'stable'}</span><div class="p-sub">${p.device_id} • ${latest}</div>`;
    b.onclick=()=>{selectedId=p.id;loadPatients();loadVitals();};
    box.appendChild(b);
  });
}

function drawCharts(vitals){
  const asc=[...vitals].reverse();
  const labels=asc.map(v=>new Date(v.timestamp).toLocaleTimeString());
  const hr=asc.map(v=>v.heart_rate), spo2=asc.map(v=>v.spo2);
  const tmp=asc.map(v=>v.temperature), sys=asc.map(v=>v.bp_systolic), dia=asc.map(v=>v.bp_diastolic);
  [chHR,chTemp,chBP].forEach(c=>{if(c)c.destroy();});
  Chart.defaults.color='#9fb0d0'; Chart.defaults.borderColor='#2b3d63';
  chHR=new Chart($('chartHR'),{type:'line',data:{labels,datasets:[
    {label:'Heart rate (bpm)',data:hr,borderColor:'#38e1c6',tension:.35},
    {label:'SpO2 (%)',data:spo2,borderColor:'#5aa2ff',tension:.35}]},options:{plugins:{legend:{labels:{color:'#eaf0ff'}}},scales:{y:{min:40,max:130}}}});
  chTemp=new Chart($('chartTemp'),{type:'line',data:{labels,datasets:[{label:'Temp (°C)',data:tmp,borderColor:'#ffc24b',tension:.35}]},options:{scales:{y:{min:34,max:40}}}});
  chBP=new Chart($('chartBP'),{type:'bar',data:{labels,datasets:[
    {label:'Systolic',data:sys,backgroundColor:'#5aa2ff'},{label:'Diastolic',data:dia,backgroundColor:'#38e1c6'}]}});
}

async function loadVitals(){
  if(!selectedId) return;
  const lim=$('rangeSel').value;
  const r=await fetch(`/api/vitals?patient_id=${selectedId}&limit=${lim}`);
  const vitals=await r.json();
  const p=patients.find(x=>x.id===selectedId);
  if(p){ $('selName').textContent=`${p.name} — ${p.condition||'Monitoring'}`;
    $('selMeta').textContent=`Age ${p.age} • ${p.gender} • Device ${p.device_id}`; }
  if(!vitals.length){ $('vitalCards').innerHTML='<p class="muted">No readings yet.</p>'; $('vitalRows').innerHTML=''; return; }
  const L=vitals[0];
  const cards=[
    ['❤️ Heart rate',`${L.heart_rate} bpm`,(L.heart_rate<50||L.heart_rate>120)],
    ['🩸 SpO₂',`${L.spo2} %`,L.spo2<92],
    ['🌡️ Temp',`${L.temperature} °C`,(L.temperature>38||L.temperature<35)],
    ['🩺 BP',`${L.bp_systolic}/${L.bp_diastolic}`,(L.bp_systolic>180||L.bp_systolic<80)],
  ];
  $('vitalCards').innerHTML=cards.map(c=>`<div class="vital ${c[2]?'bad':''}"><small>${c[0]}</small><b>${c[1]}</b></div>`).join('');
  $('vitalRows').innerHTML=vitals.map(v=>{const bad=statusOf(v);
    return `<tr><td>${new Date(v.timestamp).toUTCString()}</td><td>${v.heart_rate}</td><td>${v.spo2}</td><td>${v.temperature}</td><td>${v.bp_systolic}/${v.bp_diastolic}</td><td><span class="pill ${bad?'bad':''}">${bad?'ALERT':'normal'}</span></td></tr>`;}).join('');
  drawCharts(vitals);
}

$('addForm').onsubmit=async e=>{
  e.preventDefault();
  const fd=new FormData(e.target); const body=Object.fromEntries(fd.entries());
  const r=await fetch('/api/patients',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(r.ok){const p=await r.json();selectedId=p.id;e.target.reset();refresh();}
  else{const err=await r.json();alert('Error: '+(err.error||r.status));}
};
$('simulateBtn').onclick=async ()=>{
  if(!selectedId) return alert('Select a patient first');
  const body={patient_id:selectedId,heart_rate:55+Math.floor(Math.random()*70),
    spo2:+(90+Math.random()*9).toFixed(1),temperature:+(35.5+Math.random()*3).toFixed(1),
    bp_systolic:100+Math.floor(Math.random()*60),bp_diastolic:60+Math.floor(Math.random()*40)};
  await fetch('/api/vitals',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  refresh();
};
$('refreshBtn').onclick=refresh;
$('rangeSel').onchange=loadVitals;

async function refresh(){ await loadStats(); await loadAlerts(); await loadPatients(); await loadVitals(); }
refresh();
setInterval(refresh, 8000); // live polling every 8s
