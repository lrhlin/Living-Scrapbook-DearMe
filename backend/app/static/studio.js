'use strict';

const $ = (selector) => document.querySelector(selector);
const state = {file:null, preview:null, ready:false, busy:false, job:null, started:0, timer:null, examples:[]};
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
function setBusy(busy) {
  state.busy=busy;
  for (const input of document.querySelectorAll('#generate-form input,#generate-form textarea,#generate-form select')) input.disabled=busy;
  $('#upload-zone').disabled=busy;$('#change-photo').disabled=busy;
  $('#generate-button').disabled=busy||!state.file||!state.ready;
  $('#generate-button span').textContent=busy?'Making your keepsake…':'Make my sticker';
  for (const button of document.querySelectorAll('.example-actions button')) button.disabled=busy;
}
function selectFile(file,caption) {
  if (state.busy) return;
  if (!file || !['image/jpeg','image/png','image/webp'].includes(file.type)) {showError('Choose a JPG, PNG or WebP photo.');return;}
  if (file.size>20*1024*1024) {showError('Choose a photo smaller than 20 MB.');return;}
  if (state.preview) URL.revokeObjectURL(state.preview);
  state.file=file;state.preview=URL.createObjectURL(file);
  history.replaceState(null,'',location.pathname+'#studio');
  $('#photo-preview').src=state.preview;$('#photo-preview').alt='Reference photo: '+file.name;
  $('#selected-photo').hidden=false;$('#upload-zone').hidden=true;
  $('#photo-caption').textContent=caption||file.name;
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
  info.append(el('div',{class:'download-actions'},[
    download(sticker.svg_url,'SVG','dear-me-sticker.svg'),
    download(sticker.image_url,'PNG','dear-me-sticker.png')
  ]));
  if (options.jobId) info.append(el('a',{class:'view-original',href:'/?job='+options.jobId+'#studio',text:'View with original photo'}));
  if (options.stickerId) {
    const use=el('button',{type:'button',class:'use-in-scrapbook',text:'Use in scrapbook'});
    use.addEventListener('click',()=>window.dispatchEvent(new CustomEvent('scrapbook:pick',{detail:options.stickerId})));
    info.append(use);
  }
  return el('article',{class:'result-card'},[el('div',{class:'sticker-preview'},[image]),info]);
}
function showResult(job) {
  const original=el('article',{class:'result-card'},[
    el('div',{class:'sticker-preview'},[el('img',{src:job.source_image_url,alt:'Original reference photo'})]),
    el('div',{class:'result-info'},[el('h3',{text:'Your original photo'}),el('p',{text:'The moment your sticker started with.'})])
  ]);
  $('#result-cards').replaceChildren(original,...job.result.objects.map((obj,index)=>stickerCard(obj,{stickerId:'job:'+job.id+':'+index})));
  const usage=job.result.usage||{};
  const parts=[];
  if (typeof usage.bobcoins==='number') parts.push(Number(usage.bobcoins.toFixed(6))+' Bobcoins');
  if (typeof usage.elapsed_seconds==='number') parts.push(Math.round(usage.elapsed_seconds)+' seconds');
  if (typeof usage.total_tokens==='number') parts.push(usage.total_tokens.toLocaleString()+' tokens');
  $('#usage-summary').textContent=parts.join(' · ');
  $('#results-section').hidden=false;
  $('#results-title').textContent=job.result.objects.length===1?'A little something to keep.':'A few little things to keep.';
}
function updateElapsed() {
  const seconds=Math.max(0,Math.floor((Date.now()-state.started)/1000));
  $('#elapsed-time').textContent=Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0');
}
function showProgress(job) {
  $('#progress-panel').hidden=false;
  const messages={queued:'Your photo is in line. We’ll start illustrating it shortly.',generating:'Bob is reading your photo and illustrating the subject.',finishing:'Adding the sticker border and preparing your downloads.'};
  $('#progress-detail').textContent=messages[job.status]||'Preparing your photo…';
}
async function followJob(id) {
  let finished=false;
  try {
    while (!finished) {
      const job=await api('/jobs/'+id);state.job=job;
      if (job.status==='done') {
        finished=true;showResult(job);sessionStorage.removeItem('dearme-active-job');
        await loadLibrary();toast('Your sticker is ready and saved in your library.');
      } else if (job.status==='error') {
        finished=true;sessionStorage.removeItem('dearme-active-job');throw new Error(job.error||'Try generating your sticker again.');
      } else {showProgress(job);await new Promise(resolve=>setTimeout(resolve,1400));}
    }
  } catch(error) {showError(error.message);}
  finally {clearInterval(state.timer);$('#progress-panel').hidden=true;setBusy(false);}
}
async function generate(event) {
  event.preventDefault();if (!state.file||state.busy||!state.ready) return;
  $('#generation-error').hidden=true;$('#results-section').hidden=true;setBusy(true);
  const form=new FormData();form.append('file',state.file);
  form.append('style',$('input[name="style"]:checked').value);form.append('subject',$('#subject').value);
  form.append('instructions',$('#instructions').value);form.append('count',$('#sticker-count').value);
  try {
    const job=await api('/jobs',{method:'POST',body:form});
    history.replaceState(null,'','?job='+job.id+'#studio');
    state.started=Date.now();updateElapsed();state.timer=setInterval(updateElapsed,1000);
    sessionStorage.setItem('dearme-active-job',job.id);showProgress(job);
    await followJob(job.id);
  } catch(error) {showError(error.message);setBusy(false);}
}
async function useExample(example) {
  if (state.busy) return;
  try {
    const response=await fetch(example.original_url);if (!response.ok) throw new Error('This example photo is unavailable.');
    const blob=await response.blob();
    const file=new File([blob],example.slug+'.'+example.extension,{type:example.extension==='jpg'?'image/jpeg':'image/png'});
    selectFile(file,'Example photo · '+example.credit);
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
    const status=await api('/status');
    state.ready=status.configured&&status.cli_available&&status.renderer_available;
    $('#spend-limit').textContent=status.max_bobcoins;
    $('#connection').textContent=state.ready?'Bob is ready':'Setup needed';
    $('#connection').classList.add(state.ready?'ready':'unavailable');
    if (!state.ready) {
      $('#setup-message').hidden=false;
      $('#setup-message').textContent='To create new stickers, add your IBM Bob key to bobkey.txt at the project root and run ./start-local.sh. You can explore the examples below now.';
    }
    setBusy(false);
    const requested=new URLSearchParams(location.search).get('job');
    const active=sessionStorage.getItem('dearme-active-job')||(/^[a-f0-9]{32}$/.test(requested||'')?requested:null);
    if (active) {
      const job=await api('/jobs/'+active);
      state.started=Date.parse(job.created_at);state.job=job;
      $('#photo-preview').src=job.source_image_url;$('#selected-photo').hidden=false;$('#upload-zone').hidden=true;
      $('#subject').value=job.subject||'';$('#instructions').value=job.instructions||'';
      for (const option of document.querySelectorAll('input[name="style"]')) option.checked=option.value===job.style;
      $('#sticker-count').value=String(job.count||1);
      const savedPhoto=await fetch(job.source_image_url);
      if (savedPhoto.ok) state.file=new File([await savedPhoto.blob()],'saved-reference.png',{type:'image/png'});
      setBusy(true);updateElapsed();state.timer=setInterval(updateElapsed,1000);await followJob(active);
    }
  } catch(error) {$('#connection').textContent='Server unavailable';$('#connection').classList.add('unavailable');showError(error.message);}
}
$('#generate-form').addEventListener('submit',generate);
$('#upload-zone').addEventListener('click',()=>$('#photo-file').click());
$('#change-photo').addEventListener('click',()=>$('#photo-file').click());
$('#photo-file').addEventListener('change',event=>selectFile(event.target.files[0]));
for (const name of ['dragenter','dragover']) $('#upload-zone').addEventListener(name,event=>{event.preventDefault();if(!state.busy)$('#upload-zone').classList.add('dragging');});
for (const name of ['dragleave','drop']) $('#upload-zone').addEventListener(name,event=>{event.preventDefault();$('#upload-zone').classList.remove('dragging');if(name==='drop'&&!state.busy)selectFile(event.dataTransfer.files[0]);});
window.addEventListener('hashchange',switchView);
window.addEventListener('beforeunload',()=>{if(state.preview)URL.revokeObjectURL(state.preview);});
initialize();
