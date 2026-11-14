import { useCallback, useEffect, useMemo, useState, type ChangeEvent } from 'react';
import { Activity, ArrowRight, BarChart3, Check, CircleAlert, Clock3, Code2, Download, Eye, EyeOff, FileText, GitBranch, KeyRound, LockKeyhole, Mail, Play, ShieldAlert, ShieldCheck, ShieldHalf, Sparkles, Target, Zap } from 'lucide-react';
import './studio.css';

type Verdict = 'allow' | 'sanitize' | 'block';
type Scenario = {id:string;title:string;description:string;task:string};
type Trace = {event:string;detail?:string;content_sent?:string;tool?:string;to?:string;outcome?:string;policy_code?:string};
type Result = {answer:string;attempts:number;denied:number;hijacked:boolean;outbox:{to:string;subject:string;body:string}[];trace:Trace[]};
type Trial = {scenario_id:string;firewall_on:boolean|null;trial:number;ok:boolean;scanner_verdict?:Verdict;scan_reason?:string;duration_ms?:number;result?:Result;error_type?:string;stage?:string};
type Replays = {kind:string;generated_at:string|null;model:string|null;trials:Trial[];disclaimer:string};
type ScannerCase = {id:string;family:string;label:string;attack:boolean;expected:string;ok:boolean;actual?:string;match:boolean;flagged?:boolean;latency_ms?:number;error_type?:string};
type ScannerReport = {schema_version:number;kind:string;generated_at:string|null;method:string;cases:ScannerCase[]};
type Catalog = {scenarios:Scenario[];policies:string[];browser_budget:{hourly_limit:number;daily_limit:number;scope:string};note:string};
type Decision = {allowed:boolean;code:string;reason:string;evidence:string[];tool:string;recipient:string;authority:string};
type PolicyResult = {scenario_id:string;user_task:string;decision:Decision;effects_performed:number;model_called:boolean;simulation:string};

async function api<T>(path:string,body?:unknown):Promise<T> {
 const r=await fetch('/api/studio'+path,body===undefined?undefined:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const result=await r.json();
 if(!r.ok) throw Error(result.detail || `HTTP ${r.status}`);
 return result as T;
}
const n=(v:number)=>v.toLocaleString('en-US');
function pct(count:number,total:number) {return total ? `${Math.round(count*100/total)}%` : '—'}
function present(date:string|null) {if(!date) return 'No traces exported'; const d=new Date(date); return isNaN(d.getTime()) ? 'Unknown' : d.toLocaleString()}
function dumpCSV(rows:Trial[]){
 const head=['scenario','firewall','trial','ok','verdict','attempts','denied','fake_outbox','duration_ms','error'];
 const lines=[head.join(','),...rows.map(r=>[r.scenario_id,r.firewall_on===null?'na':r.firewall_on?'on':'off',r.trial,r.ok,r.scanner_verdict??'',r.result?.attempts??'',r.result?.denied??'',r.result?.outbox.length??'',r.duration_ms??'',r.error_type??''].map(v=>`"${String(v).replace(/"/g,'""')}"`).join(','))];
 const url=URL.createObjectURL(new Blob([lines.join('\n')],{type:'text/csv;charset=utf-8'}));
 const a=document.createElement('a'); a.href=url;a.download='airlock-real-model-trials.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function MiniIcon({on}:{on:boolean}){return on?<ShieldCheck size={16}/>:<ShieldAlert size={16}/>}
function TrialCard({trial,on}:{trial:Trial|null,on:boolean}){
 return <div className={'studio-trial '+(on?'studio-shielded':'studio-exposed')}>
  <div className="studio-trial-header"><span><MiniIcon on={on}/>{on?'AIRLOCK ON':'AIRLOCK OFF'}</span><span className="studio-trial-sub">RECORDED REAL LLM</span></div>
  {!trial?<div className="studio-missing">No completed trial for this scenario and run number.</div>:!trial.ok?<div className="studio-missing"><CircleAlert size={17}/> This trial failed during {trial.stage||'evaluation'}: {trial.error_type||'unknown error'}. It is not counted as a successful defense.</div>:
  <>
   <div className="studio-outcome-row"><span className={'studio-result '+(trial.result?.hijacked?'studio-danger':'studio-safe')}>
     {trial.scenario_id==='authorized' ? (trial.result?.outbox.length?'AUTHORIZED FAKE EMAIL':'NO FAKE EMAIL') : (trial.result?.hijacked?'UNAUTHORIZED FAKE EMAIL':'NO UNAUTHORIZED FAKE EMAIL')}</span><span className="studio-time"><Clock3 size={12}/>{trial.duration_ms||0}ms</span></div>
   <div className="studio-metrics"><div><strong>{trial.result?.attempts??0}</strong><small>TOOL ATTEMPTS</small></div><div><strong>{trial.result?.denied??0}</strong><small>GATE DENIALS</small></div><div><strong>{trial.result?.outbox.length??0}</strong><small>FAKE EMAILS</small></div></div>
   <div className="studio-timeline">
    <div className="studio-event"><span className="studio-event-dot"/><div><b>1 · Chromium inspection</b><p>Visibility scanner returned <strong>{trial.scanner_verdict?.toUpperCase()}</strong>.</p></div></div>
    {(trial.result?.trace??[]).map((event,i)=><div className="studio-event" key={i}><span className={'studio-event-dot '+(event.event==='tool_call'?'studio-event-amber':'')}/><div><b>{i+2} · {event.event==='tool_call'?'Tool boundary':'Input trust boundary'}</b><p>{event.event==='tool_call'?`${event.tool||'tool'} → ${event.to||'unknown'} · ${event.outcome||'recorded'}${event.policy_code ? ` [${event.policy_code}]` : ''}`:event.detail}</p>{event.content_sent&&<details><summary>Inspect agent-visible input</summary><pre>{event.content_sent}</pre></details>}</div></div>)}
    <div className="studio-event"><span className="studio-event-dot"/><div><b>{(trial.result?.trace?.length??0)+2} · Fake outbox</b><p>{trial.result?.outbox.length?`Contains ${trial.result.outbox.length} fake message(s). No SMTP.`:'Empty: no fake email action was executed.'}</p></div></div>
   </div>
   {!!trial.result?.outbox.length&&<div className="studio-outbox">{trial.result.outbox.map((m,i)=><div key={i}><Mail size={14}/><b>{m.to}</b><p>{m.subject}</p><p>{m.body}</p></div>)}</div>}
   <details className="studio-response"><summary>Read the model response</summary><pre>{trial.result?.answer||'No response text returned.'}</pre></details>
  </>}
 </div>
}
export default function AttackStudio(){
 const [catalog,setCatalog]=useState<Catalog|null>(null);const [replay,setReplay]=useState<Replays|null>(null);const [scannerReport,setScannerReport]=useState<ScannerReport|null>(null);const [error,setError]=useState('');
 const [scenario,setScenario]=useState('javascript');const [trialNumber,setTrialNumber]=useState(1);
 const [view,setView]=useState<'comparison'|'policy'|'evidence'>('comparison');
 const [recipient,setRecipient]=useState('audit-drop@example.invalid');const [subject,setSubject]=useState('Confidential report');const [usedActions,setUsedActions]=useState(0);const [tool,setTool]=useState('send_email');
 const [policy,setPolicy]=useState<PolicyResult|null>(null);const [policyBusy,setPolicyBusy]=useState(false);
 const refresh=useCallback(async()=>{try{const [a,b,c]=await Promise.all([api<Catalog>('/catalog'),api<Replays>('/replays'),api<ScannerReport>('/scanner-benchmark')]);setCatalog(a);setReplay(b);setScannerReport(c);setError('');}catch(e){setError(e instanceof Error?e.message:String(e))}},[]);
 useEffect(()=>{void refresh()},[refresh]);
 const scenarios=catalog?.scenarios||[];const selected=scenarios.find(s=>s.id===scenario);
 const relevant=useMemo(()=>replay?.trials.filter(x=>x.scenario_id===scenario)||[],[replay,scenario]);
 const off=relevant.find(x=>x.firewall_on===false&&x.trial===trialNumber)||null;
 const on=relevant.find(x=>x.firewall_on===true&&x.trial===trialNumber)||null;
 const summary=useMemo(()=>{
   const rows=replay?.trials.filter(x=>x.ok && x.result && x.firewall_on!==null && x.scenario_id!=='authorized')||[];
   const a=rows.filter(x=>!x.firewall_on),b=rows.filter(x=>x.firewall_on);
   return {a,b,aH:a.filter(x=>x.result!.hijacked).length,bH:b.filter(x=>x.result!.hijacked).length,
           bD:b.reduce((s,x)=>s+(x.result?.denied||0),0), totalFailures:replay?.trials.filter(x=>!x.ok).length||0};
 },[replay]);
 const runPolicy=useCallback(async()=>{setPolicyBusy(true);setPolicy(null);try{const p=await api<PolicyResult>('/policy',{scenario_id:scenario,to:recipient,subject,body:'A harmless test email for the fake outbox.',used_actions:usedActions,tool});setPolicy(p);setError('')}catch(e){setError(e instanceof Error?e.message:String(e))}finally{setPolicyBusy(false)}},[scenario,recipient,subject,usedActions,tool]);
 const maxTrial=Math.max(1,...relevant.filter(x=>x.trial>0).map(x=>x.trial));
 return <section className="studio-shell workspace">
  <div className="sectionhead"><div><div className="section-num">02 / AGENT SECURITY OBSERVATORY</div><h2>Attack. Observe. Contain.</h2><p>From invisible webpage instructions to attempted AI tool actions: inspect the full trust boundary, not just a classifier label.</p></div><span className="studio-mark"><Zap size={14}/> ATTACK REPLAY STUDIO</span></div>
  <div className="studio-kpis">
    <div><span><Activity size={14}/> REAL-MODEL TRIALS</span><strong>{n(summary.a.length+summary.b.length)}</strong><small>Completed unauthorized-action trials</small></div>
    <div><span><ShieldAlert size={14}/> ATTACK SUCCESS · OFF</span><strong>{pct(summary.aH,summary.a.length)}</strong><small>{summary.aH}/{summary.a.length} unauthorized fake-email outcomes</small></div>
    <div><span><ShieldCheck size={14}/> ATTACK SUCCESS · ON</span><strong>{pct(summary.bH,summary.b.length)}</strong><small>{summary.bH}/{summary.b.length} unauthorized fake-email outcomes</small></div>
    <div><span><LockKeyhole size={14}/> PROTECTED TOOL DENIALS</span><strong>{n(summary.bD)}</strong><small>Actual tool-gate rejections, not inferred</small></div>
  </div>
  <div className="studio-tabs" role="tablist"><button type="button" onClick={()=>setView('comparison')} className={view==='comparison'?'active':''}><GitBranch size={16}/> Attack comparison</button><button type="button" onClick={()=>{setView('policy');setPolicy(null)}} className={view==='policy'?'active':''}><Target size={16}/> Policy lab</button><button type="button" onClick={()=>setView('evidence')} className={view==='evidence'?'active':''}><BarChart3 size={16}/> Evidence & methods</button></div>
  {error&&<div className="error" role="alert"><CircleAlert size={16}/>{error}</div>}
  <div className="studio-select panel"><label htmlFor="studioScenario">ATTACK / CONTROL SCENARIO<select id="studioScenario" value={scenario} onChange={(e: ChangeEvent<HTMLSelectElement>)=>{setScenario(e.target.value);setTrialNumber(1);setPolicy(null);if(e.target.value==='authorized')setRecipient('reviewer@example.invalid');else setRecipient('audit-drop@example.invalid')}}>{scenarios.map(s=><option key={s.id} value={s.id}>{s.title}</option>)}</select></label>{view==='comparison'&&<label htmlFor="studioTrial">RECORDED TRIAL<select id="studioTrial" value={trialNumber} onChange={(e: ChangeEvent<HTMLSelectElement>)=>setTrialNumber(Number(e.target.value))}>{Array.from({length:maxTrial},(_,i)=><option key={i+1} value={i+1}>Trial {i+1}</option>)}</select></label>}<div><b>{selected?.title||'Select a scenario'}</b><p>{selected?.description}</p></div></div>
  {view==='comparison'&&<>
    <div className="studio-flow" aria-label="Execution pipeline"><span><Eye size={14}/> Browser renders</span><ArrowRight size={15}/><span><EyeOff size={14}/> Visibility split</span><ArrowRight size={15}/><span><Activity size={14}/> Model reasons</span><ArrowRight size={15}/><span><KeyRound size={14}/> Tool gate</span><ArrowRight size={15}/><span><Mail size={14}/> Fake outbox</span></div>
    {!replay?.trials.length&&<div className="studio-empty"><FileText size={27}/><strong>Evidence collection hasn't been exported yet.</strong><p>Airlock will not invent model traces. Generate real local GPT trials, review them, then publish the JSON file; this panel will populate automatically.</p><code>cd backend</code><code>.\.venv\Scripts\python.exe export_studio_replays.py --repeats 3</code></div>}
    {!!replay?.trials.length&&<div className="studio-compare"><TrialCard trial={off} on={false}/><TrialCard trial={on} on={true}/></div>}
    <div className="studio-hint"><CircleAlert size={15}/><span>Readout uses actual recorded model responses and FAKE email tools. Some unprotected runs may resist the attack; an absent tool attempt is not an action-gate denial. Both are reported honestly.</span></div>
  </>}
  {view==='policy'&&<div className="studio-policy-grid"><div className="panel studio-policy-input"><div className="studio-panel-title"><Target size={18}/> Independent action authorization</div><p>A controlled tool call is evaluated against the server-owned user request. The webpage is never allowed to grant tool permission, even if it persuades a model.</p><div className="studio-task"><small>TRUSTED USER REQUEST</small><div>{selected?.task||'Select a scenario'}</div></div><label>Tool name<select value={tool} onChange={(e: ChangeEvent<HTMLSelectElement>)=>{setTool(e.target.value);setPolicy(null)}}><option value="send_email">send_email (fake)</option><option value="shell">shell (unknown tool)</option></select></label><label>Proposed recipient<input value={recipient} maxLength={200} onChange={(e: ChangeEvent<HTMLInputElement>)=>{setRecipient(e.target.value);setPolicy(null)}}/></label><label>Subject<input value={subject} maxLength={200} onChange={(e: ChangeEvent<HTMLInputElement>)=>{setSubject(e.target.value);setPolicy(null)}}/></label><label>Actions already used<select value={usedActions} onChange={(e: ChangeEvent<HTMLSelectElement>)=>{setUsedActions(Number(e.target.value));setPolicy(null)}}><option value={0}>0</option><option value={1}>1</option><option value={2}>2</option></select></label><button className="primary" type="button" disabled={policyBusy||!selected} onClick={runPolicy}>{policyBusy?'Checking…':'Evaluate tool authorization'} <Play size={16}/></button></div>
     <div className="panel studio-policy-result"><div className="studio-panel-title"><ShieldHalf size={18}/> Authorization verdict</div>{!policy?<div className="studio-policy-blank"><LockKeyhole size={26}/><strong>Nothing can happen yet</strong><span>Propose a fake tool call and see the precise policy reasoning.</span></div>:<div className="studio-policy-decision"><div className={'studio-decision-banner '+(policy.decision.allowed?'allow':'deny')}>{policy.decision.allowed?<ShieldCheck size={25}/>:<ShieldAlert size={25}/>}<div><small>DETERMINISTIC POLICY DECISION</small><h3>{policy.decision.allowed?'AUTHORIZED':'DENIED'}</h3><p>{policy.decision.code}</p></div></div><h4>{policy.decision.reason}</h4><div className="studio-evidence-list"><b>POLICY EVIDENCE</b>{policy.decision.evidence.map((e,i)=><p key={i}><Check size={15}/>{e}</p>)}</div><div className="studio-proof"><span><Check size={14}/> 0 real emails sent</span><span><Check size={14}/> 0 LLM calls billed</span><span><Check size={14}/> 0 actions executed</span></div></div>}</div></div>}
  {view==='evidence'&&<><div className="studio-evidence"><div className="panel studio-method"><div className="studio-panel-title"><BarChart3 size={18}/> Measured outcomes</div><p>Only successful API trials for scenarios with no email consent are included in attack-success rates. Authorized-email controls are excluded. Errors are shown separately. A 0% rate with few trials does not prove an attack is impossible.</p>{[['Airlock OFF',summary.aH,summary.a.length],['Airlock ON',summary.bH,summary.b.length]].map(([label,success,total])=><div key={String(label)} className="studio-bar-item"><div><b>{label}</b><span>{success}/{total} · {pct(Number(success),Number(total))}</span></div><div className="studio-bar-track"><span style={{width:`${total?100*Number(success)/Number(total):0}%`}}/></div></div>)}<div className="studio-quantities"><span><b>{summary.totalFailures}</b> failed / inconclusive trials</span><span><b>{replay?.model||'—'}</b> actual model used</span><span><b>{present(replay?.generated_at||null)}</b> data export</span></div><button type="button" onClick={()=>dumpCSV(replay?.trials||[])} disabled={!replay?.trials.length} className="studio-outline"><Download size={15}/> Export all trial data (CSV)</button></div><div className="panel studio-method"><div className="studio-panel-title"><Code2 size={18}/> Threat model & limitations</div><ol><li><b>Attacker control:</b> HTML and JavaScript in a low-trust retrieved webpage.</li><li><b>Protected asset:</b> Agent behavior and permission to call fake tools.</li><li><b>Input boundary:</b> Chromium renders page and compares DOM text to human-visible pixels.</li><li><b>Action boundary:</b> Independent server-side policy checks tool recipient and permission.</li><li><b>Limitations:</b> Visual heuristics have false negatives/positives, and only a narrow fake-email tool is modeled.</li><li><b>Privacy:</b> Browserless runs remote Chromium. No user accounts, inbox integrations, or real SMTP are provided.</li></ol><p className="studio-disclaimer">{replay?.disclaimer||'No trials exported yet. Live scanner and recorded model evidence are independent.'}</p></div></div>
     <div className="panel studio-browser-benchmark"><div className="studio-panel-title"><Eye size={18}/> Browser visibility attack matrix</div>
     <p>Results from real Chromium scans of an independent 14-case corpus. Expected outcomes are fixed before evaluation, and incorrect results remain visible.</p>
     {!scannerReport?.cases.length?<div className="studio-empty"><strong>No browser attack-matrix results yet.</strong><p>Run the offline browser benchmark to produce actual results. No values have been fabricated.</p><code>cd backend</code><code>.\.venv\Scripts\python.exe export_scanner_benchmark.py</code></div>:<>
       <div className="studio-matrix-summary"><span><strong>{scannerReport.cases.filter(c=>c.match).length}/{scannerReport.cases.length}</strong> MATCH EXPECTATIONS</span><span><strong>{scannerReport.cases.filter(c=>c.ok&&c.attack).length}</strong> ATTACK CASES COMPLETED</span><span><strong>{scannerReport.cases.filter(c=>!c.ok).length}</strong> FAILED SCANS</span></div>
       <div className="studio-case-grid">{scannerReport.cases.map(c=><div className="studio-case" key={c.id}><span className={c.match?'studio-case-pass':'studio-case-fail'}>{c.match?'MATCH':c.ok?'MISMATCH':'ERROR'}</span><div><b>{c.label}</b><small>{c.family} · {c.attack?'ATTACK':'BENIGN CONTROL'}</small></div><code>{c.ok?c.actual||'unknown':c.error_type||'error'} / {c.expected}</code></div>)}</div>
       <p className="studio-disclaimer">{scannerReport.method} · Run {present(scannerReport.generated_at)}</p>
     </>}
     </div></>}
  <div className="studio-footer"><span><Sparkles size={15}/> AIRLOCK · THE VISIBLE / INVISIBLE TRUST BOUNDARY</span><span>ALL REPLAYED EMAILS ARE FAKE · EVIDENCE IS LABELLED</span></div>
 </section>;
}
