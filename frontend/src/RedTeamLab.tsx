import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, ArrowRight, BrainCircuit, CheckCircle2, ChevronRight, CircleAlert, FlaskConical, GitBranch, LockKeyhole, RefreshCw, ShieldAlert, ShieldCheck, Waypoints } from 'lucide-react';
import './redteam.css';

type RedCase = {id:string;title:string;category:string;description:string;trusted_task:string;steps:number;expected_protected:string};
type Overview = {case_count:number;policy_expectations_met:number;memory_quarantines:number;protected_unauthorized_executions:number;baseline_unauthorized_executions:number;simulation_only:boolean;method:string;cases:RedCase[]};
type Memory = {id:string;source:string;state:string;indicators:string[];in_context:boolean;authority_granted:boolean;excerpt:string};
type Step = {stage:string;label:string;source:string;state:string;evidence:string;policy_code?:string;indicators?:string[]};
type Policy = {step:number;tool:string;recipient:string;allowed:boolean;code:string;source:string};
type Outcome = {protected:boolean;memory:Memory[];timeline:Step[];policies:Policy[];attempts:number;denied:number;quarantined:number;fake_outbox:{to:string;subject:string}[];unauthorized_fake_actions:boolean;authority_source:string};
type Evaluation = {case:RedCase;off:Outcome;on:Outcome;method:string;limitations:string;reproducibility_hash:string};

async function readJSON<T>(url:string, init?:RequestInit):Promise<T>{
 const response=await fetch(url,init);
 const data=await response.json();
 if(!response.ok)throw new Error(data.detail||'Request failed');
 return data as T;
}
function State({value}:{value:string}){
 const bad=value==='quarantined'||value==='denied'||value==='stored_without_memory_review';
 const good=value==='allowed'||value==='facts_only'||value==='trusted'||value==='trusted_note';
 return <span className={'rt-state '+(bad?'bad':good?'good':'muted')}>{value.replaceAll('_',' ')}</span>;
}
function Lane({title, outcome, protectedLane}:{title:string;outcome:Outcome;protectedLane:boolean}){
 const [selected,setSelected]=useState(0);
 useEffect(()=>setSelected(0),[outcome]);
 const current=outcome.timeline[Math.min(selected,outcome.timeline.length-1)];
 return <article className={'rt-lane '+(protectedLane?'rt-protected':'rt-unprotected')}>
  <header><div>{protectedLane?<ShieldCheck size={20}/>:<ShieldAlert size={20}/>}<strong>{title}</strong></div>
   <span className="rt-lane-outcome">{outcome.unauthorized_fake_actions?'UNAUTHORIZED FAKE ACTION':'NO UNAUTHORIZED FAKE ACTION'}</span></header>
  <div className="rt-lane-metrics"><div><small>Memory quarantined</small><b>{outcome.quarantined}</b></div><div><small>Scripted tool proposals</small><b>{outcome.attempts}</b></div><div><small>Gate denials</small><b>{outcome.denied}</b></div><div><small>Fake outbox</small><b>{outcome.fake_outbox.length}</b></div></div>
  <div className="rt-step-list" aria-label={title+' simulation events'}>
   {outcome.timeline.map((step,i)=><button className={'rt-step '+(selected===i?'active':'')} key={i} type="button" onClick={()=>setSelected(i)}><span className="rt-step-num">{i+1}</span><span className="rt-step-body"><strong>{step.label}</strong><small>{step.source.replaceAll('_',' ')}</small></span><State value={step.state}/><ChevronRight size={14}/></button>)}
  </div>
  {current&&<div className="rt-inspector"><div className="rt-inspector-head"><span>SELECTED EVIDENCE</span><State value={current.state}/></div><p>{current.evidence}</p>{current.policy_code&&<div className="rt-inspector-code">Independent policy: <b>{current.policy_code}</b></div>}{!!current.indicators?.length&&<div className="rt-indicators">Detected: {current.indicators.join(' · ')}</div>}</div>}
  <div className="rt-memory"><b>EPHEMERAL MEMORY LEDGER</b>{outcome.memory.length?outcome.memory.map((m,i)=><div key={m.id+'-'+i}><span>{m.source.replaceAll('_',' ')}</span><State value={m.state}/><small>{m.in_context?'May appear as lower-trust data':'Excluded from protected context'}</small></div>):<p>No memories in this case.</p>}</div>
  {outcome.policies.length>0&&<div className="rt-policy-rows"><b>FAKE ACTION AUDIT</b>{outcome.policies.map(p=><div key={p.step}><span>{p.tool} → {p.recipient}</span><strong className={p.allowed?'ok':'deny'}>{p.code}</strong></div>)}</div>}
 </article>;
}
export default function RedTeamLab(){
 const [overview,setOverview]=useState<Overview|null>(null);
 const [id,setId]=useState('forged-system');
 const [evaluation,setEvaluation]=useState<Evaluation|null>(null);
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState('');
 useEffect(()=>{readJSON<Overview>('/api/redteam/overview').then(d=>{setOverview(d);if(d.cases.length)setId(d.cases[0].id)}).catch(e=>setError(String(e)))},[]);
 const run=useCallback(async(caseId:string)=>{
  setLoading(true);setError('');setEvaluation(null);
  try {setEvaluation(await readJSON<Evaluation>('/api/redteam/evaluate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({case_id:caseId})}));}
  catch(e){setError(e instanceof Error?e.message:String(e));}
  finally{setLoading(false)}
 },[]);
 useEffect(()=>{if(overview?.cases.length)run(id)},[overview,id,run]);
 const categories=useMemo(()=>Array.from(new Set(overview?.cases.map(x=>x.category)||[])),[overview]);
 const chosen=overview?.cases.find(x=>x.id===id);
 return <section className="workspace rt-shell">
  <div className="sectionhead"><div><div className="section-num">05 / MULTI-STEP SECURITY RESEARCH — SCRIPTED BASELINE</div><h2>Red-team every trust boundary.</h2><p>Investigate multi-step memory poisoning, forged authority and tool-action abuse without making real external calls.</p></div><span className="rt-flag"><FlaskConical size={16}/> RED TEAM LAB</span></div>
  <div className="rt-intro"><div className="rt-intro-symbol"><BrainCircuit size={33}/></div><div><strong>Multi-step adversarial simulation, with transparent provenance.</strong><p>All tool proposals below are <b>scripted test inputs, not LLM outputs</b>. Each memory and policy decision is executed by the actual Airlock v5 review and fake-tool policy code. This is not a measurement of live model hijack rates.</p></div></div>
  <div className="rt-kpis"><div><span>CONTROLLED CASES</span><b>{overview?.case_count??'—'}</b></div><div><span>POLICY EXPECTATIONS</span><b>{overview?`${overview.policy_expectations_met}/${overview.case_count}`:'—'}</b></div><div><span>PROTECTED UNAUTHORIZED ACTIONS</span><b>{overview?.protected_unauthorized_executions??'—'}</b></div><div><span>MEMORY QUARANTINE EVENTS</span><b>{overview?.memory_quarantines??'—'}</b></div></div>
  <div className="rt-section-head"><div><span>01 / SELECT THE ATTACK PATH</span><h3>Controlled scenarios</h3></div><div className="rt-category-count">{categories.length} categories · {overview?.case_count??'—'} tests</div></div>
  <div className="rt-case-grid">{overview?.cases.map(c=><button key={c.id} type="button" className={'rt-case '+(id===c.id?'selected':'')} onClick={()=>setId(c.id)}><span>{c.category}</span><strong>{c.title}</strong><small>{c.description}</small><div>{c.steps} processing stages <ArrowRight size={14}/></div></button>)}</div>
  <div className="rt-eval-header"><div><span>02 / REPLAY INVESTIGATION</span><h3>{chosen?.title||'Choose a scenario'}</h3><p>{chosen?.description}</p></div><button className="rt-run" disabled={!chosen||loading} onClick={()=>run(id)} type="button">{loading?<RefreshCw size={16}/>:<Activity size={16}/>} {loading?'Evaluating…':'REPLAY SCENARIO'}</button></div>
  {error&&<div className="rt-error"><CircleAlert size={18}/>{error}</div>}
  {evaluation&&<><div className="rt-authority"><LockKeyhole size={18}/><div><small>AUTHORITY ROOT · USER TASK</small><p>{evaluation.case.trusted_task}</p></div></div><div className="rt-lanes"><Lane key={id+'off'} title="AIRLOCK OFF · CONTROL" outcome={evaluation.off} protectedLane={false}/><Lane key={id+'on'} title="AIRLOCK ON · PROTECTED" outcome={evaluation.on} protectedLane={true}/></div><div className="rt-footer"><div><GitBranch size={17}/><span>Reproducibility checksum: <code>{evaluation.reproducibility_hash}</code></span></div><p>{evaluation.method}</p><p><CircleAlert size={15}/> {evaluation.limitations}</p></div></>}
  <div className="rt-next"><div><Waypoints size={22}/><div><strong>How to interpret the results</strong><p>Memory quarantine is a heuristic input defense. The independently enforced tool policy is the final authorization boundary. A simulated tool proposal does not establish that a real language model would attempt that action.</p></div></div><span><CheckCircle2 size={17}/> REAL POLICY CODE · FAKE SIDE EFFECTS</span></div>
 </section>;
}
