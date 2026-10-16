'use strict';
const $ = id => document.getElementById(id);
const addressPattern = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;
let feed, page = 0, storageAvailable = true, initialized = false;
function readStorage(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { storageAvailable=false; return fallback; } }
let watched = readStorage('dbc.watch.v1', []);
if (!Array.isArray(watched)) watched=[];
watched = [...new Set(watched.filter(x=>typeof x==='string' && addressPattern.test(x)))].slice(0,100);
let alerts = readStorage('dbc.alerts.v1', []);
if (!Array.isArray(alerts)) alerts=[];
alerts=alerts.filter(x=>x && typeof x.key==='string' && typeof x.text==='string').slice(0,100);
let seenActivity=readStorage('dbc.seen.v1',[]);
if(!Array.isArray(seenActivity))seenActivity=[];
seenActivity=seenActivity.filter(x=>typeof x==='string').slice(-1000);
function save() { try { localStorage.setItem('dbc.watch.v1',JSON.stringify(watched));localStorage.setItem('dbc.alerts.v1',JSON.stringify(alerts));localStorage.setItem('dbc.seen.v1',JSON.stringify(seenActivity)); } catch { storageAvailable=false; $('input-status').textContent='Browser storage unavailable. Changes last for this page only.'; } }
function el(tag,text,klass) { const n=document.createElement(tag); if(text!==undefined)n.textContent=text;if(klass)n.className=klass;return n; }
function short(value) { return value ? value.slice(0,7)+'...'+value.slice(-6) : 'Unresolved'; }
function matches(r) { return [r.pool,r.virtual_pool,r.base_mint].some(x=>watched.includes(x)); }
function watch(address) { if(!addressPattern.test(address))return;if(!watched.includes(address)){if(watched.length>=100){$('input-status').textContent='Watchlist limit: 100 addresses.';return;}watched.push(address);}save();render(true); }
function watchButton(address) { const b=el('button',watched.includes(address)?'\u2713':'+');b.disabled=!address || watched.includes(address);b.title='Watch '+(address||'unresolved address');b.setAttribute('aria-label',b.title);b.onclick=()=>watch(address);return b; }
function cell(row, content) { const td=el('td');td.append(typeof content==='string'?document.createTextNode(content):content);row.append(td); }
function accountLink(address) { if(!address)return el('span','Unresolved');const a=el('a',short(address));a.href='https://solscan.io/account/'+encodeURIComponent(address);a.target='_blank';a.rel='noopener noreferrer';a.title=address;return a; }
function openDetail(r) { $('detail-json').textContent=JSON.stringify(r,null,2);$('detail-links').replaceChildren();const tx=el('a','Finalized transaction source');tx.href='https://solscan.io/tx/'+encodeURIComponent(r.signature);tx.target='_blank';tx.rel='noopener noreferrer';const raw=el('a','Raw capture');raw.href='https://github.com/K9-glitch3/meteora-dbc-migration-monitor/blob/master/evidence/'+encodeURIComponent(feed.source_run)+'/capture.jsonl';raw.target='_blank';raw.rel='noopener noreferrer';$('detail-links').append(tx,raw);$('detail').showModal(); }
function addActivity(manual) {
  if(!feed)return;
  for(const r of [...feed.migrations,...feed.readiness].filter(matches)) {
    const key=(r.signature||r.virtual_pool)+':'+r.stage;
    if(seenActivity.includes(key))continue;
    const text=(manual||!initialized?'Recorded match':'Newly observed snapshot state')+' / '+r.stage+' / '+(r.pool||r.virtual_pool||r.signature)+' / captured '+r.observed_at;
    alerts.unshift({key,text});seenActivity.push(key);
  }
  alerts=alerts.slice(0,100);seenActivity=seenActivity.slice(-1000);save();initialized=true;
}
function render(manual=false) {
  $('watch-count').textContent=watched.length+' addresses';$('watchlist').replaceChildren();
  for(const address of watched) { const row=el('div',undefined,'watch-item');const b=el('button','\u00d7');b.title='Remove '+address;b.setAttribute('aria-label',b.title);b.onclick=()=>{watched=watched.filter(a=>a!==address);save();render();};row.append(el('code',address),b);$('watchlist').append(row); }
  if(!feed)return;
  addActivity(manual);
  const only=$('watch-only').checked;
  const readiness=feed.readiness.filter(r=>!only||matches(r));$('readiness-rows').replaceChildren();
  for(const r of readiness) { const tr=el('tr');cell(tr,accountLink(r.virtual_pool));cell(tr,el('span',r.stage,'stage-pill'));const p=el('div',r.progress_bps===undefined?'Unknown':(r.progress_bps/100).toFixed(2)+'%');if(r.progress_bps!==undefined){const bar=el('progress');bar.max=10000;bar.value=r.progress_bps;p.append(bar);}cell(tr,p);cell(tr,String(r.slot));cell(tr,watchButton(r.virtual_pool));$('readiness-rows').append(tr); }
  $('readiness-empty').hidden=readiness.length!==0;
  const search=$('search').value.trim().toLowerCase();const stage=$('stage').value;
  const rows=feed.migrations.filter(r=>(!only||matches(r))&&(!stage||r.stage===stage)&&(!search||[r.pool,r.virtual_pool,r.base_mint,r.signature].filter(Boolean).some(v=>v.toLowerCase().includes(search))));
  const pages=Math.max(1,Math.ceil(rows.length/25));page=Math.min(page,pages-1);$('migration-rows').replaceChildren();
  for(const r of rows.slice(page*25,(page+1)*25)) { const tr=el('tr');cell(tr,r.observed_at.slice(11,19));const identity=el('div');identity.append(accountLink(r.pool),el('br'),el('code',short(r.signature)));cell(tr,identity);cell(tr,el('span',r.stage,'stage-pill '+r.stage));cell(tr,r.reason.replaceAll('_',' '));const detail=el('button','Inspect');detail.onclick=()=>openDetail(r);cell(tr,detail);cell(tr,watchButton(r.pool||r.virtual_pool));$('migration-rows').append(tr); }
  $('migration-count').textContent=rows.length+' observations';$('migration-empty').hidden=rows.length!==0;$('page').textContent='Page '+(page+1)+' of '+pages;$('previous').disabled=page===0;$('next').disabled=page>=pages-1;
  $('alerts').replaceChildren(...alerts.map(a=>el('li',a.text)));$('alerts-empty').hidden=alerts.length!==0;
}
async function refresh() {
  $('refresh').disabled=true;
  try { const response=await fetch('api/v1/feed.json',{cache:'no-store',signal:AbortSignal.timeout(15000)});if(!response.ok)throw new Error('HTTP '+response.status);const data=await response.json();
    if(data.api_version!=='1.0'||data.mode!=='recorded_snapshot'||!Array.isArray(data.migrations)||!Array.isArray(data.readiness))throw new Error('Unsupported feed');
    feed=data;$('migration-time').textContent=feed.migration_recorded_until;$('readiness-time').textContent=feed.readiness_recorded_until;
    const stale=[feed.migration_recorded_until,feed.readiness_recorded_until].some(t=>!Number.isFinite(Date.parse(t))||Date.now()-Date.parse(t)>feed.limits.stale_after_seconds*1000);
    $('status').className=stale?'error':'';$('status').textContent=(stale?'Historical / stale snapshot':'Recent recorded snapshot')+' · Not a continuous live feed'+(feed.readiness_errors.length?' · Readiness collection errors retained':'');render();
  } catch(error) { $('status').className='error';$('status').textContent='Refresh failed. '+(feed?'Previously loaded data retained. ':'')+error.message; }
  finally { $('refresh').disabled=false; }
}
$('watch-form').onsubmit=e=>{e.preventDefault();$('input-status').textContent='';const address=$('address').value.trim();if(!addressPattern.test(address)){$('input-status').textContent='Enter a valid Solana address.';return;}watch(address);$('address').value='';};
$('refresh').onclick=refresh;$('watch-only').onchange=()=>{page=0;render();};$('search').oninput=()=>{page=0;render();};$('stage').onchange=()=>{page=0;render();};$('previous').onclick=()=>{page--;render();};$('next').onclick=()=>{page++;render();};$('close-detail').onclick=()=>$('detail').close();$('clear-alerts').onclick=()=>{alerts=[];save();$('alerts').replaceChildren();$('alerts-empty').hidden=false;};
setInterval(()=>{if($('auto-refresh').checked&&!document.hidden)refresh();},60000);
render();refresh();
