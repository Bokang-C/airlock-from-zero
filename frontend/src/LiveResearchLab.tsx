import {useEffect, useMemo, useState} from 'react';
import {Activity, ArrowRight, BrainCircuit, CheckCircle2, CircleAlert, Database, FlaskConical, GitCompareArrows, LockKeyhole, ShieldAlert, ShieldCheck} from 'lucide-react';
import './live-research.css';

type Case = {id:string;title:string;category:string;description:string;steps:number;trusted_task:string};
type Catalog = {cases:Case[];live_inference_from_public_api:boolean;method:string};
type Policy = {tool:string;recipient:string;allowed:boolean;policy_code:string;source:string;proposal_number:number};
type Memory = {source:string;label:string;state:string;review_id:string;indicators:string[];available_to_model:boolean;excerpt:string;authority_granted:boolean};
type Step = {step:number;event_label:string;event_source:string;memory:Memory;model_output:string;model_tool_attempts:number;model_tool_calls_truncated:number;tools:Policy[];model_output_state:string|null};
type Trial = {case_id:string;case_title:string;category:string;protected:boolean;trial:number;trusted_task:string;model:string;status:'completed'|'error';error_category?:string;model_calls:number;attempts:number;denied:number;fake_outbox:{to:string;subject:string;step:number;action_kind:string}[];unauthorized_fake_actions:boolean;memory_quarantined:number;steps:Step[]};
type Summary = {case_id:string;protected:boolean;completed_trials:number;unauthorized_fake_trials:number;fake_actions:number;denied_tool_attempts:number;actual_tool_attempts:number;quarantined_memories:number};
type Evidence = {schema_version:number;kind:string;generated_at:string|null;model?:string;trials:Trial[];summary:Summary[];method:string;limitations?:string;public_execution:boolean};

async function getJSON<T>(url:string):Promise<T>{
 const res=await fetch(url);const value=await res.json();
 if(!res.ok)throw new Error(typeof value.detail==='string'?value.detail:'The research endpoint is unavailable');
 return value as T;
}
function Stat({label,value,note}:{label:string;value:string|number;note?:string}){
 return <div className="lr-stat"><span>{label}</span><strong>{value}</strong>{note&&<small>{note}</small>}</div>;
}
function StageCard({stage}:{stage:Step}){
 return <article className="lr-step"><div className="lr-step-top"><span>STEP {stage.step} · {stage.event_source.replaceAll('_',' ')}</span><strong>{stage.event_label}</strong></div>
  <div className="lr-state-row"><span>Memory review</span><b className={stage.memory.state==='quarantined'?'lr-red':'lr-green'}>{stage.memory.state.replaceAll('_',' ')}</b></div>
  <p className="lr-content">{stage.memory.excerpt}</p>
  {!!stage.memory.indicators?.length&&<p className="lr-indicators">Indicators: {stage.memory.indicators.join(' · ')}</p>}
  <div className="lr-state-row"><span>Included in next model context?</span><b>{stage.memory.available_to_model?'YES — UNTRUSTED DATA':'NO — QUARANTINED'}</b></div>
  {stage.model_output&&<div className="lr-model"><span>MODEL OUTPUT · NEXT-TURN MEMORY: {stage.model_output_state?.replaceAll('_',' ')||'not recorded'}</span><p>{stage.model_output}</p></div>}
  {stage.tools.length>0&&<div className="lr-tool-list"><span>ACTUAL MODEL TOOL PROPOSALS</span>{stage.tools.map((t,i)=><div key={i} className={'lr-tool '+(t.allowed?'lr-allowed':'lr-rejected')}><div><strong>{t.tool}</strong><small>→ {t.recipient||'(none)'}</small></div><b>{t.policy_code}</b></div>)}</div>}
  {!stage.tools.length&&<p className="lr-no-tool">The model did not propose a tool action at this step.</p>}
 </article>;
}
function Lane({trial,title}:{trial?:Trial;title:string}){
 const [selected,setSelected]=useState(0);
 useEffect(()=>setSelected(0),[trial]);
 if(!trial)return <section className="lr-lane lr-empty"><header>{title}</header><p>No completed model trial recorded for this configuration.</p></section>;
 const selectedStage=trial.steps[Math.min(selected,trial.steps.length-1)];
 return <section className={'lr-lane '+(trial.protected?'lr-on':'lr-off')}>
  <header><div>{trial.protected?<ShieldCheck size={19}/>:<ShieldAlert size={19}/>}<strong>{title}</strong></div><span>{trial.unauthorized_fake_actions?'UNAUTHORIZED FAKE ACTION':'NO UNAUTHORIZED FAKE ACTION'}</span></header>
  <div className="lr-lane-stats"><div><small>Model calls</small><b>{trial.model_calls}</b></div><div><small>Tool attempts</small><b>{trial.attempts}</b></div><div><small>Denied</small><b>{trial.denied}</b></div><div><small>Fake outbox</small><b>{trial.fake_outbox.length}</b></div></div>
  <div className="lr-timeline" aria-label={title+' model steps'}>{trial.steps.map((s,i)=><button key={s.step} onClick={()=>setSelected(i)} className={selected===i?'selected':''}><span>{s.step}</span><div><b>{s.event_label}</b><small>{s.memory.state.replaceAll('_',' ')}</small></div><ArrowRight size={14}/></button>)}</div>
  {selectedStage&&<StageCard stage={selectedStage}/>}
  <div className="lr-outbox"><b>FAKE OUTBOX · {trial.fake_outbox.length} MESSAGE(S)</b>{trial.fake_outbox.length?trial.fake_outbox.map((m,i)=><p key={i}>Step {m.step}: {m.to} — {m.subject}</p>):<p>No fake emails were written.</p>}</div>
 </section>;
}
export default function LiveResearchLab(){
 const [catalog,setCatalog]=useState<Catalog|null>(null);const [evidence,setEvidence]=useState<Evidence|null>(null);
 const [id,setId]=useState('recipient-pivot');const [trialNumber,setTrialNumber]=useState(1);const [error,setError]=useState('');
 useEffect(()=>{Promise.all([getJSON<Catalog>('/api/live-research/catalog'),getJSON<Evidence>('/api/live-research/replays')])
  .then(([a,b])=>{setCatalog(a);setEvidence(b);if(b.trials.length)setId(b.trials[0].case_id);else if(a.cases.length)setId(a.cases[0].id)})
  .catch(e=>setError(e instanceof Error?e.message:String(e)))},[]);
 const available=useMemo(()=>evidence?.trials.filter(t=>t.case_id===id&&t.status==='completed')||[],[evidence,id]);
 const numbers=useMemo(()=>Array.from(new Set(available.map(x=>x.trial))).sort((a,b)=>a-b),[available]);
 useEffect(()=>setTrialNumber(numbers[0]||1),[id,evidence]);
 const off=available.find(t=>t.trial===trialNumber&&!t.protected);const on=available.find(t=>t.trial===trialNumber&&t.protected);
 const chosen=catalog?.cases.find(c=>c.id===id);
 const records=evidence?.trials||[];const complete=records.filter(t=>t.status==='completed').length;
 const totalAttacks=records.filter(t=>t.status==='completed'&&t.unauthorized_fake_actions).length;
 const missing=records.filter(t=>t.status==='error').length;
 return <section className="workspace lr-shell">
  <div className="sectionhead"><div><div className="section-num">06 / REAL-MODEL MULTI-STEP INVESTIGATION</div><h2>Observe what the AI actually tried.</h2><p>Replay real model decisions across multiple untrusted observations. Every tool action is fake, every policy outcome is traceable.</p></div><span className="lr-badge"><Activity size={15}/> LIVE RESEARCH</span></div>
  <div className="lr-intro"><BrainCircuit size={30}/><div><strong>Recorded real-model experiments. No scripted tool proposals.</strong><p>These trials use actual OpenAI model calls performed locally, reviewed, and then published as read-only evidence. The public website never starts research runs or triggers additional paid requests in this section.</p></div></div>
  {error&&<div className="lr-alert"><CircleAlert size={18}/>{error}</div>}
  <div className="lr-stats"><Stat label="COMPLETED MODEL TRIALS" value={complete}/><Stat label="UNAUTHORIZED FAKE OUTCOMES" value={totalAttacks}/><Stat label="FAILED / INCOMPLETE TRIALS" value={missing}/><Stat label="RECORDED RESEARCH CASES" value={new Set(records.map(r=>r.case_id)).size}/></div>
  {!records.length?<div className="lr-awaiting"><Database size={32}/><h3>Awaiting reviewed live research evidence</h3><p>Run the local exporter on your own computer. Review its pending JSON before publishing. The v5 scripted RED TEAM tab remains available now.</p><code>python export_live_research_v6.py --dry-run</code><p>This page intentionally does not invent results or make public model calls.</p></div>:
   <><div className="lr-head"><div><span>01 / CHOOSE AN EXPERIMENT</span><h3>Real-model evidence library</h3></div><small>Model: {evidence?.model||'not recorded'} · {complete} completed</small></div>
    <div className="lr-casegrid">{catalog?.cases.map(c=><button key={c.id} onClick={()=>setId(c.id)} className={id===c.id?'active':''}><span>{c.category}</span><strong>{c.title}</strong><small>{c.description}</small><em>{available.length&&id===c.id?`${available.length} completed lane records`:''}</em></button>)}</div>
    <div className="lr-head"><div><span>02 / RECONSTRUCT THE DECISION CHAIN</span><h3>{chosen?.title||id}</h3><p>{chosen?.description}</p></div>{numbers.length>0&&<label>REPEATED TRIAL<select value={trialNumber} onChange={e=>setTrialNumber(Number(e.target.value))}>{numbers.map(n=><option key={n} value={n}>Trial {n}</option>)}</select></label>}</div>
    <div className="lr-task"><LockKeyhole size={17}/><div><small>ONLY TRUSTED AUTHORITY · USER TASK</small><p>{chosen?.trusted_task||off?.trusted_task||on?.trusted_task}</p></div></div>
    <div className="lr-lanes"><Lane title="AIRLOCK OFF · CONTROL" trial={off}/><Lane title="AIRLOCK ON · PROTECTED" trial={on}/></div>
   </>}
  <div className="lr-caveat"><FlaskConical size={21}/><div><b>Experimental design and limitations</b><p>{evidence?.limitations||'Live trial evidence is not yet available.'}</p><p>All email recipients use reserved .invalid domains and actions remain inside a fake outbox. The model may independently refuse malicious instructions. Quarantine is heuristic and the tool gateway is a separate defense. Trial failures are not counted as successful protection.</p></div></div>
  <div className="lr-foot"><GitCompareArrows size={17}/> <span>{evidence?.method||'Local billable inference only, published through reviewed recordings.'}</span><CheckCircle2 size={16}/></div>
 </section>;
}
