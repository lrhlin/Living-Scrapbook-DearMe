'use strict';

const $ = (selector) => document.querySelector(selector);
// files: array of {file, preview, caption}
const state = {files:[], ready:false, busy:false, job:null, started:0, timer:null, examples:[]};
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
  $('#upload-zone').disabled=busy;
  $('#generate-button').disabled=busy||state.files.length===0||!state.ready;
  $('#generate-button span').textContent=busy?'Making your keepsakes…':'Make my sticker'+(state.files.length>1?' ('+state.files.length+' photos)':'');
  for (const button of document.querySelectorAll('.example-actions button')) button.disabled=busy;
}
function renderPhotoGrid() {
  const grid=$('#photo-grid');
  grid.replaceChildren();
  if (state.files.length===0) {
    $('#upload-zone').hidden=false;
    $('#photo-grid-section').hidden=true;
    return;
  }
  $('#upload-zone').hidden=true;
  $('#photo-grid-section').hidden=false;
  state.files.forEach((entry,index)=>{
    const img=el('img',{src:entry.preview,alt:'Reference photo '+(index+1),loading:'lazy'});
    const remove=el('button',{type:'button',class:'photo-remove','aria-label':'Remove photo '+(index+1),text:'×'});
    remove.addEventListener('click',()=>{
      if (state.busy) return;
      URL.revokeObjectURL(entry.preview);
      state.files.splice(index,1);
      renderPhotoGrid();setBusy(false);
    });
    const card=el('div',{class:'photo-thumb'},[img,remove,el('span',{class:'photo-thumb-name',text:entry.caption||entry.file.name})]);
    grid.append(card);
  });
  // "Add more" button
  if (!state.busy) {
    const addMore=el('button',{type:'button',class:'photo-add-more',text:'+ Add more'});
    addMore.addEventListener('click',()=>$('#photo-file').click());
    grid.append(addMore);
  }
  setBusy(state.busy);
}
function addFiles(fileList, captionOverride) {
  if (state.busy) return;
  let added=0;
  for (const file of Array.from(fileList||[])) {
    if (!['image/jpeg','image/png','image/webp'].includes(file.type)) {showError('Choose JPG, PNG or WebP photos.');continue;}
    if (file.size>20*1024*1024) {showError(file.name+' is larger than 20 MB — skipped.');continue;}
    state.files.push({file,preview:URL.createObjectURL(file),caption:captionOverride||file.name});
    added++;
  }
  if (added>0) {
    history.replaceState(null,'',location.pathname+'#studio');
    $('#generation-error').hidden=true;$('#results-section').hidden=true;
  }
  renderPhotoGrid();
}
// Keep selectFile for backward-compat with example loading
function selectFile(file,caption) {
  if (state.busy) return;
  if (!file || !['image/jpeg','image/png','image/webp'].includes(file.type)) {showError('Choose a JPG, PNG or WebP photo.');return;}
  if (file.size>20*1024*1024) {showError('Choose a photo smaller than 20 MB.');return;}
  // Replace all current files with this one (used by examples)
  for (const e of state.files) URL.revokeObjectURL(e.preview);
  state.files=[{file,preview:URL.createObjectURL(file),caption:caption||file.name}];
  history.replaceState(null,'',location.pathname+'#studio');
  $('#generation-error').hidden=true;$('#results-section').hidden=true;
  renderPhotoGrid();setBusy(false);
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
async function generateOne(entry, style, subject, instructions, count) {
  const form=new FormData();
  form.append('file',entry.file);
  form.append('style',style);form.append('subject',subject);
  form.append('instructions',instructions);form.append('count',count);
  const job=await api('/jobs',{method:'POST',body:form});
  return job;
}
async function generate(event) {
  event.preventDefault();if (state.files.length===0||state.busy||!state.ready) return;
  $('#generation-error').hidden=true;$('#results-section').hidden=true;setBusy(true);
  const style=$('input[name="style"]:checked').value;
  const subject=$('#subject').value;
  const instructions=$('#instructions').value;
  const count=parseInt($('#sticker-count').value)||1;
  // Submit each photo as a separate job, then follow all in sequence
  try {
    const jobs=[];
    for (const entry of state.files) {
      const job=await generateOne(entry,style,subject,instructions,count);
      jobs.push(job);
    }
    if (jobs.length===1) {
      history.replaceState(null,'','?job='+jobs[0].id+'#studio');
      sessionStorage.setItem('dearme-active-job',jobs[0].id);
    }
    state.started=Date.now();updateElapsed();state.timer=setInterval(updateElapsed,1000);
    showProgress(jobs[0]);
    // Follow each job in sequence and accumulate results
    const allResults=[];
    for (const job of jobs) {
      const result=await followJobReturn(job.id);
      if (result) allResults.push(result);
    }
    if (allResults.length>0) showMultiResult(allResults);
    await loadLibrary();toast(allResults.length===1?'Your sticker is ready and saved in your library.':'Your stickers are ready and saved in your library.');
  } catch(error) {showError(error.message);setBusy(false);}
}
// Like followJob but returns the job instead of rendering directly
async function followJobReturn(id) {
  try {
    while (true) {
      const job=await api('/jobs/'+id);state.job=job;
      if (job.status==='done') {sessionStorage.removeItem('dearme-active-job');return job;}
      else if (job.status==='error') {sessionStorage.removeItem('dearme-active-job');throw new Error(job.error||'Try generating your sticker again.');}
      else {showProgress(job);await new Promise(resolve=>setTimeout(resolve,1400));}
    }
  } finally {clearInterval(state.timer);$('#progress-panel').hidden=true;setBusy(false);}
}
function showMultiResult(jobs) {
  const cards=[];
  for (const job of jobs) {
    const original=el('article',{class:'result-card'},[
      el('div',{class:'sticker-preview'},[el('img',{src:job.source_image_url,alt:'Original reference photo'})]),
      el('div',{class:'result-info'},[el('h3',{text:'Your original photo'}),el('p',{text:'The moment your sticker started with.'})])
    ]);
    cards.push(original,...job.result.objects.map((obj,index)=>stickerCard(obj,{stickerId:'job:'+job.id+':'+index})));
  }
  $('#result-cards').replaceChildren(...cards);
  if (jobs.length===1) {
    const usage=jobs[0].result.usage||{};
    const parts=[];
    if (typeof usage.bobcoins==='number') parts.push(Number(usage.bobcoins.toFixed(6))+' Bobcoins');
    if (typeof usage.elapsed_seconds==='number') parts.push(Math.round(usage.elapsed_seconds)+' seconds');
    if (typeof usage.total_tokens==='number') parts.push(usage.total_tokens.toLocaleString()+' tokens');
    $('#usage-summary').textContent=parts.join(' · ');
  } else {
    $('#usage-summary').textContent=jobs.length+' photos processed';
  }
  $('#results-section').hidden=false;
  const total=jobs.reduce((n,j)=>n+(j.result.objects?.length||0),0);
  $('#results-title').textContent=total===1?'A little something to keep.':'A few little things to keep.';
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
      $('#subject').value=job.subject||'';$('#instructions').value=job.instructions||'';
      for (const option of document.querySelectorAll('input[name="style"]')) option.checked=option.value===job.style;
      $('#sticker-count').value=String(job.count||1);
      const savedPhoto=await fetch(job.source_image_url);
      if (savedPhoto.ok) {
        const file=new File([await savedPhoto.blob()],'saved-reference.png',{type:'image/png'});
        state.files=[{file,preview:job.source_image_url,caption:'saved-reference.png'}];
        renderPhotoGrid();
      }
      setBusy(true);updateElapsed();state.timer=setInterval(updateElapsed,1000);
      const result=await followJobReturn(active);
      if (result) showMultiResult([result]);
      await loadLibrary();
    }
  } catch(error) {$('#connection').textContent='Server unavailable';$('#connection').classList.add('unavailable');showError(error.message);}
}
$('#generate-form').addEventListener('submit',generate);
$('#upload-zone').addEventListener('click',()=>$('#photo-file').click());
$('#photo-file').addEventListener('change',event=>{addFiles(event.target.files);event.target.value='';});
for (const name of ['dragenter','dragover']) $('#upload-zone').addEventListener(name,event=>{event.preventDefault();if(!state.busy)$('#upload-zone').classList.add('dragging');});
for (const name of ['dragleave','drop']) $('#upload-zone').addEventListener(name,event=>{event.preventDefault();$('#upload-zone').classList.remove('dragging');if(name==='drop'&&!state.busy)addFiles(event.dataTransfer.files);});
window.addEventListener('hashchange',switchView);
window.addEventListener('beforeunload',()=>{if(state.preview)URL.revokeObjectURL(state.preview);});
initialize();
