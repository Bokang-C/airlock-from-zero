import { useCallback, useEffect, useMemo, useState, type ChangeEvent } from 'react';
import { Activity, ArrowRight, ArrowLeft, BookOpen, CheckCircle2, ChevronRight, CircleAlert, Eye, EyeOff, GitBranch, Globe2, LockKeyhole, Mail, Play, RefreshCw, ScanEye, ShieldAlert, ShieldCheck, ShieldHalf, Waypoints } from 'lucide-react';
import './provenance.css';

type Node = {id:string;label:string;layer:string;state:string;evidence:string;source:string;observed:boolean;note:string};
type Edge = {from:string;to:string;kind:string;note:string};
type Graph = {available:boolean;reason?:string;firewall_on:boolean;trial:number;nodes?:Node[];edges?:Edge[];measured?:{attempts:number;denied:number;fake_outbox:number;hijacked:boolean;duration_ms?:number};grounding?:string};
type Pair = {scenario:{id:string;title:string;description:string;task:string};model?:string;generated_at?:string;off:Graph;on:Graph;disclaimer:string};
type Overview = {scenarios:{id:string;title:string;description:string;trial_numbers:number[]}[];model:string|null;generated_at:string|null;trial_count:number};
type PageScenario = {id:string;html:string;task:string;title:string};
type Segment = {text:string;visibility:string;suspicious:boolean;dom_path?:string|null;signals:string[];reasons:string[];bbox?:{x:number;y:number;width:number;height:number}|null};
type FreshScan = {verdict:string;reason:string;segments:Segment[];screenshot_base64:string;stats:Record<string,number>};
const STEPS = [
 {id:'source',title:'The attacker controls the page',icon:Globe2,detail:'The user request is trusted; the retrieved HTML is not. Airlock keeps those authorities distinct.',off:'page',on:'user'},
 {id:'render',title:'Chromium reveals the hidden text',icon:ScanEye,detail:'Airlock renders the sample, extracts DOM text, and records a visibility verdict.',off:'render',on:'render'},
 {id:'context',title:'The input boundary changes what the model sees',icon:EyeOff,detail:'Compare the actual recorded context excerpts, not a reconstructed transcript.',off:'context',on:'context'},
 {id:'model',title:'Observe—not assume—the model response',icon:Activity,detail:'The model might comply, refuse, or skip tools. Each recorded outcome counts.',off:'model',on:'model'},
 {id:'tool',title:'An action needs independent authorization',icon:LockKeyhole,detail:'The Action Gateway checks explicit user permission only if a tool is proposed.',off:'tool',on:'policy'},
 {id:'effect',title:'Verify the fake outbox',icon:Mail,detail:'Count executed fake actions. An empty outbox is not proof that the gateway was exercised.',off:'effect',on:'effect'},
];
const STAGES = ['page','render','context','model','tool','policy','effect'];
async function getJSON<T>(url:string,init?:RequestInit):Promise<T>{
 const r = await fetch(url,init); const body=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(typeof body.detail==='string'?body.detail:`Request failed (${r.status})`);
 return body as T;
}
function nodeOf(graph:Graph|undefined,key:string):Node|undefined{return graph?.nodes?.find(n=>n.id===key)}
function Tone({value}:{value:string}){return <span className={'prov-tone state-'+value.replace(/[^a-z-]/g,'')}>{value.replace(/-/g,' ').toUpperCase()}</span>}
function EvidenceCard({graph,nodeId}:{graph:Graph;nodeId:string}){
 if(!graph.available) return <div className="prov-empty"><CircleAlert size={19}/>{graph.reason||'No recorded experiment for this configuration.'}</div>;
 const node=nodeOf(graph,nodeId);
 if(!node)return <div className="prov-empty">This evidence item was not recorded.</div>;
 return <div className="prov-evidence"><div className="prov-evidence-top"><span>{node.label}</span><Tone value={node.state}/></div><p>{node.evidence}</p><div className="prov-evidence-footer"><span>{node.observed?'RECORDED / SERVER-OWNED':'INFERRED OR MISSING'}</span><span>{node.source}</span></div><small>{node.note}</small></div>;
}
function GraphTrack({graph,label,selected,onSelect}:{graph:Graph;label:string;selected:string;onSelect:(id:string)=>void}){
 const on=graph.firewall_on;
 return <div className={'prov-track '+(on?'prov-on':'prov-off')}>
  <div className="prov-track-head"><strong>{on?<ShieldCheck size={18}/>:<ShieldAlert size={18}/>} {label}</strong><span>{graph.available?'RECORDED REAL-MODEL TRIAL':'NO AVAILABLE TRIAL'}</span></div>
  {!graph.available?<p className="prov-missing">{graph.reason}</p>:<>
   <div className="prov-trusted"><LockKeyhole size={14}/> Authority: <strong>trusted user request</strong><span>{nodeOf(graph,'user')?.evidence}</span></div>
   <div className="prov-nodes" role="group" aria-label={label+' provenance stages'}>
    {STAGES.map((id,index)=>{const node=nodeOf(graph,id);return <div key={id} className="prov-node-slot"><button type="button" aria-pressed={selected===id} className={'prov-node '+(selected===id?'selected ':'')+'state-'+(node?.state||'missing')} onClick={()=>onSelect(id)}><span>{String(index+1).padStart(2,'0')}</span><b>{node?.label||id}</b><small>{node?.state||'unknown'}</small></button>{index<STAGES.length-1&&<ChevronRight aria-hidden size={17} className="prov-connector"/>}</div>})}
   </div>
   <div className="prov-metrics"><span><b>{graph.measured?.attempts??0}</b> tool proposals</span><span><b>{graph.measured?.denied??0}</b> denied</span><span><b>{graph.measured?.fake_outbox??0}</b> fake emails</span><span className={graph.measured?.hijacked?'prov-danger':'prov-ok'}>{graph.measured?.hijacked?'UNAUTHORIZED ACTION RECORDED':'NO UNAUTHORIZED ACTION RECORDED'}</span></div>
   <EvidenceCard graph={graph} nodeId={selected}/>
  </>}
 </div>;
}
export default function ProvenanceLab({onOpenScanner}:{onOpenScanner?:(scenarioId:string)=>void}){
 const [overview,setOverview]=useState<Overview|null>(null);
 const [scenario,setScenario]=useState('javascript');const [trial,setTrial]=useState(1);
 const [pair,setPair]=useState<Pair|null>(null);const [error,setError]=useState('');
 const [busy,setBusy]=useState(false);const [mode,setMode]=useState<'guide'|'graph'|'rescan'>('guide');
 const [step,setStep]=useState(0);const [selected,setSelected]=useState('context');
 const [fresh,setFresh]=useState<FreshScan|null>(null);const [freshLoading,setFreshLoading]=useState(false);
 const [freshError,setFreshError]=useState('');const [focusSeg,setFocusSeg]=useState<number|null>(null);
 useEffect(()=>{getJSON<Overview>('/api/provenance/overview').then(d=>{
  setOverview(d);const preferred=d.scenarios.find(s=>s.id==='javascript'&&s.trial_numbers.length) || d.scenarios.find(s=>s.trial_numbers.length);
  if(preferred){setScenario(preferred.id);setTrial(preferred.trial_numbers[0]);}
 }).catch(e=>setError(String(e)))},[]);
 useEffect(()=>{let cancelled=false;setBusy(true);setError('');setPair(null);
  getJSON<Pair>(`/api/provenance/compare?scenario_id=${encodeURIComponent(scenario)}&trial=${trial}`)
    .then(d=>{if(!cancelled)setPair(d)}).catch(e=>{if(!cancelled)setError(String(e))}).finally(()=>{if(!cancelled)setBusy(false)});
  return()=>{cancelled=true};
 },[scenario,trial]);
 const chosen=overview?.scenarios.find(s=>s.id===scenario);
 const available=chosen?.trial_numbers??[];
 const exportAt=useMemo(()=>pair?.generated_at?new Date(pair.generated_at).toLocaleString():'No recorded trials', [pair?.generated_at]);
 const refreshBrowser=useCallback(async()=>{
  setFresh(null);setFocusSeg(null);setFreshError('');setFreshLoading(true);
  try{
   const catalog=await getJSON<PageScenario[]>('/api/scenarios');const sample=catalog.find(x=>x.id===scenario);
   if(!sample)throw new Error('Scenario HTML not available');
   const result=await getJSON<FreshScan>('/api/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:sample.html})});
   setFresh(result);
  }catch(e){setFreshError(e instanceof Error?e.message:String(e))}finally{setFreshLoading(false)}
 },[scenario]);
 const current=STEPS[step];
 const chooseScenario=(next:string)=>{setScenario(next);setTrial(overview?.scenarios.find(s=>s.id===next)?.trial_numbers[0]||1);setStep(0);setSelected('context');setFresh(null)};
 return <section className="workspace prov-shell">
  <div className="sectionhead"><div><div className="section-num">04 / TRUST PROVENANCE + INVESTIGATION</div><h2>Follow the attack. Prove the outcome.</h2><p>Reconstruct how low-trust webpage text crossed—or failed to cross—the boundaries around a real AI agent.</p></div><span className="prov-flag"><Waypoints size={15}/> AIRLOCK SECURITY INVESTIGATOR</span></div>
  <div className="prov-banner"><div className="prov-banner-icon"><GitBranch size={28}/></div><div><small>TRANSPARENT BY DESIGN</small><h3>Evidence, not invented intelligence.</h3><p>Every model action and gate decision below comes from a recorded experiment. The pipeline connections describe system structure; they do not prove what the model was thinking.</p></div><div className="prov-export"><span>REPLAY DATASET</span><b>{overview?.trial_count??'—'} trial records</b><small>{exportAt}</small></div></div>
  <div className="prov-controls panel"><label>INVESTIGATION<select value={scenario} onChange={(e:ChangeEvent<HTMLSelectElement>)=>chooseScenario(e.target.value)}>{overview?.scenarios.map(x=><option key={x.id} value={x.id}>{x.title}</option>)}</select></label><label>RECORDED TRIAL<select value={trial} onChange={(e:ChangeEvent<HTMLSelectElement>)=>{setTrial(Number(e.target.value));setFresh(null)}}>{available.length?available.map(x=><option key={x} value={x}>Trial {x}</option>):<option value={1}>No recorded trials</option>}</select></label><div className="prov-control-note">{chosen?.description||'Loading scenario catalog'}<br/><b>Model:</b> {pair?.model||overview?.model||'not recorded'}</div></div>
  <div className="prov-tabs" role="group" aria-label="Investigation modes"><button type="button" className={mode==='guide'?'active':''} onClick={()=>setMode('guide')}><BookOpen size={17}/> Judge Mode</button><button type="button" className={mode==='graph'?'active':''} onClick={()=>setMode('graph')}><GitBranch size={17}/> Provenance Graph</button><button type="button" className={mode==='rescan'?'active':''} onClick={()=>setMode('rescan')}><ScanEye size={17}/> Fresh Browser Evidence</button></div>
  {error&&<div className="error" role="alert"><CircleAlert size={17}/>{error}</div>}
  {busy&&<div className="prov-loading"><RefreshCw size={17}/> Loading verified trial evidence…</div>}
  {pair&&mode==='guide'&&<div className="prov-judge">
    <div className="prov-chapter panel"><div className="prov-chapter-head"><span>GUIDED INVESTIGATION</span><b>{step+1} / {STEPS.length}</b></div><div className="prov-progress"><span style={{width:`${(step+1)/STEPS.length*100}%`}}/></div>
    <div className="prov-chapters">{STEPS.map((s,i)=><button type="button" key={s.id} className={step===i?'current':''} onClick={()=>setStep(i)}><span>{i+1}</span>{s.title}</button>)}</div>
    <div className="prov-guide-actions"><button disabled={step===0} onClick={()=>setStep(x=>Math.max(0,x-1))}><ArrowLeft size={15}/> Back</button><button className="primary" onClick={()=>{if(step===STEPS.length-1){setMode('graph');setSelected('context')}else setStep(x=>x+1)}}>{step===STEPS.length-1?'Open full graph':'Next finding'} <ArrowRight size={15}/></button></div>
    </div><div className="prov-chapter-content panel"><div className="prov-chapter-kicker"><current.icon size={18}/> SECURITY BOUNDARY {step+1}</div><h3>{current.title}</h3><p>{current.detail}</p>
    <div className="prov-compare"><div className="prov-compare-pane"><header><ShieldAlert size={17}/> AIRLOCK OFF</header><EvidenceCard graph={pair.off} nodeId={current.off}/></div><div className="prov-compare-pane"><header><ShieldCheck size={17}/> AIRLOCK ON</header><EvidenceCard graph={pair.on} nodeId={current.on}/></div></div>
    <div className="prov-explainer"><CircleAlert size={17}/>{step===4?'A gate denial only counts if a model proposed a tool action and that denial was recorded.':'Recorded results can differ between runs even with the same sample and model.'}</div>
    </div></div>}
  {pair&&mode==='graph'&&<div className="prov-graph">
    <p className="prov-graph-sub">Select any stage on either track to inspect the recorded evidence. These are pipeline stages—not a proof of causal influence.</p>
    <GraphTrack graph={pair.off} label="FIREWALL OFF" selected={selected} onSelect={setSelected}/>
    <GraphTrack graph={pair.on} label="FIREWALL ON" selected={selected} onSelect={setSelected}/>
    <div className="prov-grounding"><CheckCircle2 size={16}/> {pair.disclaimer}</div>
    </div>}
  {mode==='rescan'&&<div className="prov-live panel"><div className="prov-live-head"><div><span><ScanEye size={17}/> LIVE CHROMIUM EVIDENCE</span><h3>Re-scan the selected sample</h3><p>This calls the working Browserless-backed X-Ray API. The new screenshot is <strong>not from the historical LLM replay</strong>.</p></div><button className="primary" type="button" onClick={refreshBrowser} disabled={freshLoading}>{freshLoading?'Scanning…':'Run fresh browser scan'} <Play size={16}/></button></div>
    {freshError&&<div className="error" role="alert">{freshError}</div>}
    {!fresh&&!freshLoading&&<div className="prov-empty-live"><Eye size={25}/> Choose “Run fresh browser scan” to obtain a new screenshot and DOM observations. This consumes a Browserless session.</div>}
    {fresh&&<><div className="prov-live-result"><span>FRESH VERDICT</span><Tone value={fresh.verdict}/><span>{fresh.reason}</span></div><div className="prov-live-grid"><div className="prov-viewport"><img src={'data:image/png;base64,'+fresh.screenshot_base64} alt="Fresh Chromium-rendered screenshot"/>{fresh.segments.map((s,i)=>s.suspicious&&s.bbox&&s.bbox.width>0&&s.bbox.height>0?<button title={'Inspect segment '+(i+1)} aria-label={'Inspect suspicious region '+(i+1)} type="button" onClick={()=>setFocusSeg(i)} key={i} className={'prov-rect '+(focusSeg===i?'active':'')} style={{left:`${s.bbox.x/1060*100}%`,top:`${s.bbox.y/670*100}%`,width:`${s.bbox.width/1060*100}%`,height:`${s.bbox.height/670*100}%`}}/>:null)}</div><div className="prov-segments"><b>DOM EVIDENCE · {fresh.segments.length} SEGMENTS</b>{fresh.segments.map((s,i)=><button key={i} type="button" className={focusSeg===i?'selected':''} onClick={()=>setFocusSeg(i)}><span>{s.suspicious?'⚠':'·'} {s.visibility.toUpperCase()} · {s.dom_path||'Path unavailable'}</span><small>{s.text.slice(0,160)}</small>{focusSeg===i&&<em>{s.bbox?'Screenshot box observed':'No measurable screenshot box'} · {s.reasons.join(', ')||'No visibility anomalies'} · {s.signals.join(', ')||'No suspicious-language signal'}</em>}</button>)}</div></div></>}
    {onOpenScanner&&<button type="button" className="prov-open-scanner" onClick={()=>onOpenScanner(scenario)}>Open this HTML in the full X-Ray Scanner <ArrowRight size={15}/></button>}
    </div>}
  {pair&&<div className="prov-footer"><ShieldHalf size={16}/><span>{pair.disclaimer}</span></div>}
 </section>;
}
