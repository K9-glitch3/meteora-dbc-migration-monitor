"use strict";
const $ = id => document.getElementById(id);
const labels = {SUPPORTED_COMPARISON:"Identity matched",NO_CONCLUSION:"No conclusion",UNSUPPORTED_CONFIGURATION:"Unsupported",REJECTED_OBSERVATION:"Rejected"};
let dataset, records = [], filtered = [], page = 0, request = 0;
const pageSize = 50;
function cell(text, cls) { const td=document.createElement("td"); td.textContent=text; if(cls)td.className=cls; return td; }
function short(value) { return value ? value.slice(0,8)+"..."+value.slice(-6) : "-"; }
function when(value) { return new Date(value).toISOString().replace("T"," ").replace("Z"," UTC"); }
function detail(record) {
  $("detail-summary").replaceChildren();
  for(const [key,value] of Object.entries({Source:record.source,Stage:record.stage,Scope:record.scope,Commitment:record.commitment,Freshness:record.freshness,Result:labels[record.verdict],Reason:record.reason})) {
    const dt=document.createElement("dt"), dd=document.createElement("dd");dt.textContent=key;dd.textContent=value;$("detail-summary").append(dt,dd);
  }
  $("detail-links").replaceChildren();
  if(record.source==="mainnet_capture") {
    for(const [type,value] of [["tx",record.signature],["account",record.pool]]) if(value) {
      const link=document.createElement("a");link.textContent=type==="tx"?"Solana transaction":"Pool account";link.href="https://explorer.solana.com/"+type+"/"+encodeURIComponent(value);link.target="_blank";link.rel="noopener";$("detail-links").append(link);
    }
  }
  $("detail-json").textContent=JSON.stringify(record,null,2);
  $("detail").showModal();
}
function render() {
  const query=$("search").value.trim().toLowerCase();
  filtered=records.filter(r=>(!$("verdict").value||r.verdict===$("verdict").value)&&(!$("stage").value||r.stage===$("stage").value)&&(!$("freshness").value||r.freshness===$("freshness").value)&&(!query||[r.pool,r.signature,r.reason,r.slot,r.id].join(" ").toLowerCase().includes(query)));
  const pages=Math.max(1,Math.ceil(filtered.length/pageSize));page=Math.min(page,pages-1);
  const fragment=document.createDocumentFragment();
  for(const r of filtered.slice(page*pageSize,(page+1)*pageSize)) {
    const tr=document.createElement("tr");
    tr.append(cell(when(r.observed_at).slice(11,23)),cell(r.stage),cell(r.slot??"-"));
    const key=cell(""),code=document.createElement("code");code.textContent=short(r.pool||r.signature);code.title=r.pool||r.signature||"";key.append(code);tr.append(key);
    const result=cell(""),tag=document.createElement("span");tag.className="tag "+r.verdict;tag.textContent=labels[r.verdict];result.append(tag);tr.append(result,cell(r.reason.replaceAll("_"," "),"reason"));
    const action=cell(""),button=document.createElement("button");button.textContent="View";button.setAttribute("aria-label","View observation "+r.sequence);button.addEventListener("click",()=>detail(r));action.append(button);tr.append(action);fragment.append(tr);
  }
  $("rows").replaceChildren(fragment);$("empty").hidden=filtered.length!==0;
  $("count").textContent=filtered.length.toLocaleString()+" / "+records.length.toLocaleString()+" records";
  $("page").textContent="Page "+(page+1)+" of "+pages;$("previous").disabled=page===0;$("next").disabled=page===pages-1;
  $("download").disabled=filtered.length===0;
}
function timeline() {
  const canvas=$("activity"),bounds=canvas.getBoundingClientRect(),ratio=window.devicePixelRatio||1;
  canvas.width=Math.max(1,Math.round(bounds.width*ratio));canvas.height=88*ratio;
  const context=canvas.getContext("2d");context.scale(ratio,ratio);context.clearRect(0,0,bounds.width,88);
  if(!records.length){$("timeline-label").textContent="";return;}
  const times=records.map(r=>Date.parse(r.observed_at)),min=Math.min(...times),max=Math.max(...times);
  const bins=Array(60).fill(0);for(const t of times)bins[Math.min(59,Math.floor((t-min)/Math.max(1,max-min)*60))]++;
  const peak=Math.max(1,...bins),width=bounds.width/60;context.fillStyle="#d8e2dc";context.fillRect(0,86,bounds.width,1);
  bins.forEach((n,i)=>{if(!n)return;context.fillStyle="#32896b";const height=Math.max(2,n/peak*76);context.fillRect(i*width+1,85-height,Math.max(1,width-2),height);});
  $("timeline-label").textContent=new Date(min).toISOString().slice(11,19)+" - "+new Date(max).toISOString().slice(11,19)+" UTC";
}
async function loadDataset(item) {
  const token=++request;
  $("status").className="";$("status").textContent="Loading evidence...";
  dataset=null;
  for(const id of ["source","recorded","duration"])$(id).textContent="Pending";
  for(const id of ["migration-count","pool-count","distinct-count","health-count"])$(id).textContent="0";
  for(const id of ["manifest","capture"])$(id).removeAttribute("href");
  records=[];render();timeline();
  try {
    const response=await fetch("data/"+item.file);if(!response.ok)throw Error("Evidence download failed ("+response.status+")");
    const data=await response.json();if(token!==request)return;
    if(!Array.isArray(data.observations)||!data.manifest)throw Error("Invalid dataset format");
    dataset=data;records=data.observations;page=0;
    const m=data.manifest,isReal=m.source==="mainnet_capture";
    $("source").textContent=isReal?"Mainnet capture":"Synthetic tests";
    $("recorded").textContent=when(m.started_at);
    $("duration").textContent=Math.max(0,(Date.parse(m.ended_at)-Date.parse(m.started_at))/1000).toFixed(1)+" seconds";
    const base="https://github.com/K9-glitch3/meteora-dbc-migration-monitor/blob/master/evidence/"+encodeURIComponent(item.evidence)+"/";
    $("manifest").href=base+"manifest.json";$("capture").href=base+"capture.jsonl";
    $("migration-count").textContent=records.filter(r=>r.stage==="FINALIZED"&&r.verdict==="SUPPORTED_COMPARISON").length;
    $("pool-count").textContent=records.filter(r=>r.stage==="POOL_STATE").length;
    $("distinct-count").textContent=new Set(records.map(r=>r.pool).filter(Boolean)).size;
    $("health-count").textContent=records.filter(r=>r.stage==="HEALTH").length;
    $("status").textContent=isReal?"Recorded mainnet evidence. Checksums and deterministic replay are verified in CI.":"Synthetic test fixture. These records are not blockchain activity.";
    render();timeline();
  } catch(error) {if(token!==request)return;$("status").className="error";$("status").textContent=error.message+" Please reload to retry."; }
}
for(const id of ["search","verdict","stage","freshness"])$(id).addEventListener(id==="search"?"input":"change",()=>{page=0;render();});
$("previous").addEventListener("click",()=>{page--;render();});$("next").addEventListener("click",()=>{page++;render();});
$("close-detail").addEventListener("click",()=>$("detail").close());
$("download").addEventListener("click",()=>{
  const blob=new Blob([JSON.stringify({source:dataset.manifest.source,comparison_scope:dataset.manifest.comparison_scope,filtered_observations:filtered},null,2)],{type:"application/json"});
  const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="dbc-observations.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
window.addEventListener("resize",timeline);
(async()=>{
  try {
    const response=await fetch("data/index.json");if(!response.ok)throw Error("Dataset index is unavailable");
    const items=await response.json();if(!Array.isArray(items)||!items.length)throw Error("No datasets published");
    for(const item of items){const option=document.createElement("option");option.value=item.id;option.textContent=item.label;$("dataset").append(option);}
    $("dataset").addEventListener("change",()=>loadDataset(items.find(item=>item.id===$("dataset").value)));
    await loadDataset(items[0]);
  } catch(error){$("status").className="error";$("status").textContent=error.message;}
})();
