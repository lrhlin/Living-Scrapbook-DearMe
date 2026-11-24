'use strict';

const $ = (selector) => document.querySelector(selector);
const MAX_PHOTOS=3;
const state = {files:[], previews:[], ready:false, busy:false, job:null, started:0, timer:null, examples:[], provider:'openai', status:null};
const providerNames={openai:'OpenAI',bob:'IBM Bob'};
const names = {scrapbook:'My scrapbook', studio:'Sticker studio', library:'My sticker library', workflow:'How it works'};
const styleNames = {paper:'Paper cut', soft:'Soft illustration', ink:'Ink sketch'};

function el(tag, attributes={}, children=[]) {
  const node=document.createElement(tag);
  for (const [name,value] of Object.entries(attributes)) {
    if (name==='class') node.className=value;
    else if (name==='text') node.textContent=value;
    else node.setAttribute(name,value);
  }
  for (const child of children) if (child) node.append(child);
  return node;
}
function icon(name) {
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('aria-hidden','true');
  const use=document.createElementNS('http://www.w3.org/2000/svg','use');
  use.setAttribute('href','#i-'+name);svg.append(use);return svg;
}
async function api(path,options) {
  const response=await fetch('/api/v1/studio'+path,options);
  let body;
  try {body=await response.json();} catch {throw new Error('Restart the local server and try again.');}
  if (!response.ok) throw new Error(typeof body.detail==='string'?body.detail:'Please try again.');
  return body;
}
function toast(message) {
  $('#toast').textContent=message;$('#toast').hidden=false;
  clearTimeout(toast.timeout);toast.timeout=setTimeout(()=>{$('#toast').hidden=true;},4000);
}
function showError(message) {$('#generation-error').textContent=message;$('#generation-error').hidden=false;}
function selectProvider(value) {
  state.provider=value==='bob'?'bob':'openai';
  localStorage.setItem('dearme-sticker-provider',state.provider);
  $('#sticker-provider').value=state.provider;
  const provider=state.status.providers[state.provider];
  state.ready=provider.ready;
  $('#provider-detail').textContent=provider.model+' · '+provider.key_file;
  $('#connection').textContent=state.ready?provider.name+' is ready':'Set up '+provider.name;
  $('#connection').classList.toggle('ready',state.ready);$('#connection').classList.toggle('unavailable',!state.ready);
  $('#setup-message').hidden=state.ready;
  $('#setup-message').textContent='Add your '+provider.name+' API key to '+provider.key_file+' at the project root, then refresh the page.';
  $('#provider-cost').textContent=state.provider==='openai'
    ?'Uses your OpenAI API account · 1024 × 1024 PNG. Each variation is a generated image.'
    :'Uses IBM Bob · '+state.status.max_bobcoins+' Bobcoins limit per photo. Includes SVG and PNG.';
  $('#sticker-count-label').textContent=state.provider==='openai'?'Sticker variations per photo':'Maximum stickers from this photo';
  for (const option of $('#sticker-count').options) {
    const amount=Number(option.value);
    option.textContent=amount===1?'1 sticker':state.provider==='openai'?amount+' variations':'Up to '+amount+' stickers';
  }
  setBusy(state.busy);
}
function setBusy(busy) {
  state.busy=busy;
  for (const input of document.querySelectorAll('#generate-form input,#generate-form textarea,#generate-form select')) input.disabled=busy;
  $('#upload-zone').disabled=busy;$('#change-photo').disabled=busy;
  $('#generate-button').disabled=busy||!state.files.length||!state.ready;
  $('#generate-button span').textContent=busy?'Making your keepsake…':state.files.length>1?'Make my stickers':'Make my sticker';
  for (const button of document.querySelectorAll('.example-actions button')) button.disabled=busy;
}
function selectFiles(files,caption) {
  if (state.busy) return;
  const selected=Array.from(files||[]);
  if (!selected.length) return;
  if (selected.length>MAX_PHOTOS) {showError('Choose up to 3 photos at a time.');return;}
  if (selected.some(file=>!['image/jpeg','image/png','image/webp'].includes(file.type))) {showError('Choose JPG, PNG or WebP photos.');return;}
  if (selected.some(file=>file.size>20*1024*1024)) {showError('Each photo must be smaller than 20 MB.');return;}
  state.previews.forEach(URL.revokeObjectURL);
  state.files=selected;state.previews=selected.map(file=>URL.createObjectURL(file));
  history.replaceState(null,'',location.pathname+'#studio');
  $('#photo-preview-list').replaceChildren(...selected.map((file,index)=>el('img',{src:state.previews[index],alt:'Reference photo: '+file.name,title:file.name})));
  $('#selected-photo').hidden=false;$('#upload-zone').hidden=true;
  $('#photo-caption').textContent=caption||selected.map(file=>file.name).join(' · ');
  $('#generation-error').hidden=true;$('#results-section').hidden=true;
  setBusy(false);
}
function switchView() {
  const requestedView=location.hash.slice(1);
  const view=Object.hasOwn(names,requestedView)?requestedView:'scrapbook';
  for (const name of Object.keys(names)) $('#'+name+'-view').hidden=name!==view;
  for (const link of document.querySelectorAll('[data-view]')) {
    const active=link.dataset.view===view;link.classList.toggle('active',active);
    if (active) link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');
  }
  $('#page-name').textContent=names[view];document.title='Dear Me — '+names[view];
  if (view==='library') loadLibrary();
  if (view==='scrapbook') window.dispatchEvent(new Event('scrapbook:open'));
}
function download(url,label,filename) {
  const separator=url.includes('?')?'&':'?';
  return el('a',{href:url+separator+'download=true',download:filename},[icon('download'),el('span',{text:label})]);
}
function stickerCard(sticker,options={}) {
  const image=el('img',{src:sticker.image_url,alt:sticker.label,loading:'lazy'});
  const info=el('div',{class:'result-info'});
  if (options.date) info.append(el('div',{class:'library-date',text:options.date}));
  info.append(el('h3',{text:sticker.label}),el('p',{text:sticker.description||styleNames[sticker.style]||'Your illustrated sticker'}));
  info.append(el('p',{class:'sticker-format',text:(providerNames[sticker.provider||'bob'])+' · '+(sticker.format==='png'?'PNG':'SVG + PNG')}));
  const downloads=[download(sticker.image_url,'PNG','dear-me-sticker.png')];
  if (sticker.svg_url) downloads.unshift(download(sticker.svg_url,'SVG','dear-me-sticker.svg'));
  info.append(el('div',{class:'download-actions'},downloads));
  if (options.jobId) info.append(el('a',{class:'view-original',href:'/?job='+options.jobId+'#studio',text:'View with original photo'}));
  if (options.stickerId) {
    const use=el('button',{type:'button',class:'use-in-scrapbook',text:'Use in scrapbook'});
    use.addEventListener('click',()=>window.dispatchEvent(new CustomEvent('scrapbook:pick',{detail:options.stickerId})));
    info.append(use);
  }
  return el('article',{class:'result-card'},[el('div',{class:'sticker-preview'},[image]),info]);
}
function showResults(jobs) {
  const cards=[],models=new Set();let bobcoins=0,seconds=0,tokens=0;
  for (const job of jobs) {
    cards.push(el('article',{class:'result-card'},[
      el('div',{class:'sticker-preview'},[el('img',{src:job.source_image_url,alt:'Original reference photo: '+job.photo_name})]),
      el('div',{class:'result-info'},[el('h3',{text:job.photo_name||'Your original photo'}),el('p',{text:'The moment this sticker started with.'})])
    ]));
    cards.push(...job.result.objects.map((obj,index)=>stickerCard(obj,{stickerId:'job:'+job.id+':'+index})));
    const usage=job.result.usage||{};
    models.add(usage.model||providerNames[job.provider||'bob']);
    if (typeof usage.bobcoins==='number') bobcoins+=usage.bobcoins;
    if (typeof usage.elapsed_seconds==='number') seconds+=usage.elapsed_seconds;
    if (typeof usage.total_tokens==='number') tokens+=usage.total_tokens;
  }
  $('#result-cards').replaceChildren(...cards);
  const parts=[...models];
  if (bobcoins) parts.push(Number(bobcoins.toFixed(6))+' Bobcoins');
  if (seconds) parts.push(Math.round(seconds)+' seconds');
  if (tokens) parts.push(tokens.toLocaleString()+' tokens');
  $('#usage-summary').textContent=parts.join(' · ');
  $('#results-section').hidden=false;
  $('#results-title').textContent=jobs.length===1?'A little something to keep.':jobs.length+' photos, ready to keep.';
}
function updateElapsed() {
  const seconds=Math.max(0,Math.floor((Date.now()-state.started)/1000));
  $('#elapsed-time').textContent=Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0');
}
function showProgress(job) {
  $('#progress-panel').hidden=false;
  const messages={queued:'Your photo is in line. We’ll start illustrating it shortly.',generating:providerNames[job.provider||state.provider]+' is illustrating your photo.',finishing:'Preparing your sticker downloads.'};
  $('#progress-detail').textContent=messages[job.status]||'Preparing your photo…';
}
async function followJobs(jobs) {
  const pending=new Map(jobs.map((job,index)=>[job.id,{...job,photo_name:job.photo_name||'Photo '+(index+1)}]));
  const completed=[],errors=[];
  while (pending.size) {
    await Promise.all([...pending.entries()].map(async([id,summary])=>{
      const job=await api('/jobs/'+id);state.job=job;
      if (job.status==='done') {completed.push({...job,photo_name:summary.photo_name});pending.delete(id);}
      else if (job.status==='error') {errors.push(summary.photo_name+': '+(job.error||'Try generating this sticker again.'));pending.delete(id);}
    }));
    if (pending.size) {
      const finished=completed.length+errors.length;
      $('#progress-panel').hidden=false;
      $('#progress-title').textContent=finished+' of '+jobs.length+' photos complete';
      $('#progress-detail').textContent=providerNames[[...pending.values()][0].provider||'bob']+' is illustrating each photo in the queue.';
      await new Promise(resolve=>setTimeout(resolve,1400));
    }
  }
  sessionStorage.removeItem('dearme-active-jobs');sessionStorage.removeItem('dearme-active-job');
  return {completed,errors};
}
async function generate(event) {
  event.preventDefault();if (!state.files.length||state.busy||!state.ready) return;
  $('#generation-error').hidden=true;$('#results-section').hidden=true;setBusy(true);
  const files=[...state.files],jobs=[],style=$('input[name="style"]:checked').value;
  const subject=$('#subject').value,instructions=$('#instructions').value,count=$('#sticker-count').value;
  let uploadError=null;
  try {
    for (let index=0;index<files.length;index++) {
      const file=files[index],form=new FormData();form.append('file',file);
      form.append('style',style);form.append('subject',subject);form.append('instructions',instructions);form.append('count',count);
      form.append('provider',state.provider);
      $('#progress-panel').hidden=false;$('#progress-title').textContent='Uploading photo '+(index+1)+' of '+files.length;
      try {jobs.push({...await api('/jobs',{method:'POST',body:form}),photo_name:file.name});}
      catch(error) {uploadError=error.message;break;}
    }
    if (!jobs.length) {if(uploadError)throw new Error(uploadError);return;}
    history.replaceState(null,'','?job='+jobs.at(-1).id+'#studio');
    state.started=Date.now();updateElapsed();state.timer=setInterval(updateElapsed,1000);
    sessionStorage.setItem('dearme-active-jobs',JSON.stringify(jobs.map(job=>job.id)));
    const result=await followJobs(jobs);
    if (result.completed.length) {showResults(result.completed);await loadLibrary();toast(result.completed.length===1?'Your sticker is ready and saved in your library.':result.completed.length+' photos are saved in your library.');}
    const problems=[...result.errors];if(uploadError)problems.push(uploadError);
    if (problems.length) showError(result.completed.length+' of '+files.length+' photos completed. '+problems.join(' '));
  } catch(error) {showError(error.message);}
  finally {clearInterval(state.timer);$('#progress-panel').hidden=true;setBusy(false);}
}
async function useExample(example) {
  if (state.busy) return;
  try {
    const response=await fetch(example.original_url);if (!response.ok) throw new Error('This example photo is unavailable.');
    const blob=await response.blob();
    const file=new File([blob],example.slug+'.'+example.extension,{type:example.extension==='jpg'?'image/jpeg':'image/png'});
    selectFiles([file],'Example photo · '+example.credit);
    $('#subject').value=example.subject;
    $('#instructions').value=example.slug==='cat'?'A portrait of the face and ears, with the whiskers included.':'';
    location.hash='studio';$('#photo-title').scrollIntoView({behavior:'smooth',block:'start'});
    toast('Photo selected. Choose a feeling, then make your sticker.');
  } catch(error) {showError(error.message);}
}
async function loadExamples() {
  try {
    state.examples=await api('/examples');
    const cards=state.examples.map(example=>{
      const button=el('button',{type:'button',text:'Use this photo'});button.addEventListener('click',()=>useExample(example));
      return el('article',{class:'example-card'},[
        el('div',{class:'example-photo '+(example.slug==='tree'?'tree-photo':'')},[
          el('img',{class:'reference',src:example.original_url,alt:example.subject+' reference photograph',loading:'lazy'}),
          el('img',{class:'example-sticker',src:example.sticker_url,alt:'Illustrated '+example.subject+' sticker',loading:'lazy'})
        ]),
        el('div',{class:'example-body'},[
          el('h3',{text:example.title}),el('p',{text:example.subject+' · '+example.credit}),
          el('div',{class:'example-actions'},[button,el('a',{href:example.source,target:'_blank',rel:'noopener',text:'Photo source'})])
        ])
      ]);
    });
    $('#examples-grid').replaceChildren(...cards);
  } catch {$('#examples-grid').replaceChildren(el('p',{class:'example-note',text:'Upload a photo above to create your sticker.'}));}
}
async function loadLibrary() {
  try {
    const jobs=(await api('/jobs')).filter(job=>job.status==='done'&&job.result);
    const cards=jobs.flatMap(job=>job.result.objects.map((obj,index)=>stickerCard(obj,{jobId:job.id,stickerId:'job:'+job.id+':'+index,date:new Date(job.created_at).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'})+' · '+(styleNames[job.style]||job.style)})));
    $('#library-grid').replaceChildren(...cards);$('#library-empty').hidden=cards.length>0;
    $('#library-count').textContent=cards.length;
    window.dispatchEvent(new Event('scrapbook:stickers-updated'));
  } catch {$('#library-grid').replaceChildren(el('p',{class:'error-message',text:'Start the local server, then refresh your library.'}));}
}
async function initialize() {
  switchView();loadExamples();loadLibrary();
  try {
    state.status=await api('/status');
    selectProvider(localStorage.getItem('dearme-sticker-provider')||state.status.default_provider);
    const requested=new URLSearchParams(location.search).get('job');
    const rawJobs=sessionStorage.getItem('dearme-active-jobs');
    let activeJobs=[];
    try {activeJobs=rawJobs?JSON.parse(rawJobs):[];} catch {}
    if (!activeJobs.length) {
      const active=sessionStorage.getItem('dearme-active-job')||(/^[a-f0-9]{32}$/.test(requested||'')?requested:null);
      if (active) activeJobs=[active];
    }
    if (activeJobs.length) {
      const jobs=await Promise.all(activeJobs.map(id=>api('/jobs/'+id)));
      const job=jobs[0];
      state.started=Date.parse(job.created_at);state.job=job;
      $('#photo-preview-list').replaceChildren(...jobs.map((item,index)=>el('img',{src:item.source_image_url,alt:'Saved reference photo '+(index+1)})));$('#selected-photo').hidden=false;$('#upload-zone').hidden=true;
      $('#subject').value=job.subject||'';$('#instructions').value=job.instructions||'';
      for (const option of document.querySelectorAll('input[name="style"]')) option.checked=option.value===job.style;
      $('#sticker-count').value=String(job.count||1);
      const savedPhoto=await fetch(job.source_image_url);
      if (savedPhoto.ok) state.files=[new File([await savedPhoto.blob()],'saved-reference.png',{type:'image/png'})];
      setBusy(true);updateElapsed();state.timer=setInterval(updateElapsed,1000);
      const result=await followJobs(jobs.map((item,index)=>({...item,photo_name:'Photo '+(index+1)})));
      if (result.completed.length) {showResults(result.completed);await loadLibrary();}
      if (result.errors.length) showError(result.errors.join(' '));
      setBusy(false);
    }
  } catch(error) {$('#connection').textContent='Server unavailable';$('#connection').classList.add('unavailable');showError(error.message);}
  finally {clearInterval(state.timer);$('#progress-panel').hidden=true;setBusy(false);}
}
$('#generate-form').addEventListener('submit',generate);
$('#sticker-provider').addEventListener('change',event=>selectProvider(event.target.value));
$('#upload-zone').addEventListener('click',()=>$('#photo-file').click());
$('#change-photo').addEventListener('click',()=>$('#photo-file').click());
$('#photo-file').addEventListener('change',event=>{selectFiles(event.target.files);event.target.value='';});
for (const name of ['dragenter','dragover']) $('#upload-zone').addEventListener(name,event=>{event.preventDefault();if(!state.busy)$('#upload-zone').classList.add('dragging');});
for (const name of ['dragleave','drop']) $('#upload-zone').addEventListener(name,event=>{event.preventDefault();$('#upload-zone').classList.remove('dragging');if(name==='drop'&&!state.busy)selectFiles(event.dataTransfer.files);});
window.addEventListener('hashchange',switchView);
window.addEventListener('beforeunload',()=>state.previews.forEach(URL.revokeObjectURL));
initialize();
