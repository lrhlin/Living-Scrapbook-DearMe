'use strict';

(() => {
  const book={catalog:[],selected:new Map(),current:null,page:0,busy:false,loading:null};
  const today=()=>{const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');};
  const formatDate=value=>new Date(value+'T12:00:00').toLocaleDateString(undefined,{year:'numeric',month:'long',day:'numeric'});
  const smooth=()=>matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth';

  async function bookApi(path,options) {
    const response=await fetch('/api/v1/scrapbook'+path,options);
    let value;
    try {value=await response.json();} catch {throw new Error('Start the local server, then try again.');}
    if (!response.ok) {
      const detail=Array.isArray(value.detail)?value.detail.map(item=>item.msg).join(' '):value.detail;
      throw new Error(detail||'Please try adding your entry again.');
    }
    return value;
  }
  function error(message) {$('#entry-error').textContent=message;$('#entry-error').hidden=false;}
  function updateControls() {
    const amount=book.selected.size;
    $('#selected-sticker-count').textContent=amount+' selected';
    $('#clear-sticker-selection').disabled=book.busy||!amount;
    $('#entry-character-count').textContent=$('#entry-text').value.length.toLocaleString()+' / 20,000';
    $('#entry-add').disabled=book.busy||(!amount&&!$('#entry-text').value.trim());
  }
  function setBusy(busy) {
    book.busy=busy;
    for (const field of document.querySelectorAll('#entry-form input,#entry-form textarea,#sticker-picker-grid input')) field.disabled=busy;
    $('#entry-add span').textContent=busy?'Arranging pages…':'Add';
    $('#entry-saving').hidden=!busy;
    updateControls();
  }
  function renderPicker() {
    const term=$('#sticker-search').value.trim().toLowerCase();
    const source=$('#sticker-source').value;
    const visible=book.catalog.filter(item=>item.label.toLowerCase().includes(term)
      &&(source==='all'||(source==='yours')===item.id.startsWith('job:')));
    const cards=visible.map(item=>{
      const checkbox=el('input',{type:'checkbox','aria-label':'Select '+item.label});
      checkbox.checked=book.selected.has(item.id);checkbox.disabled=book.busy;
      checkbox.addEventListener('change',()=>{
        if (checkbox.checked) {
          if (book.selected.size>=50) {checkbox.checked=false;toast('You can use up to 50 stickers in one entry.');return;}
          book.selected.set(item.id,item);
        } else book.selected.delete(item.id);
        checkbox.closest('label').classList.toggle('selected',checkbox.checked);updateControls();
      });
      return el('label',{class:'sticker-choice'+(checkbox.checked?' selected':'')},[
        checkbox,el('img',{src:item.image_url,alt:'',loading:'lazy'}),
        el('strong',{text:item.label}),el('span',{class:'sticker-choice-source',text:item.source})
      ]);
    });
    $('#sticker-picker-grid').replaceChildren(...cards);$('#picker-empty').hidden=cards.length>0;
    updateControls();
  }
  async function loadStickers() {
    book.catalog=await bookApi('/stickers');renderPicker();
  }
  async function loadEntries() {
    const entries=await bookApi('/entries');
    $('#scrapbook-count').textContent=entries.length;
    $('#saved-entry-total').textContent=entries.length?entries.length+' saved '+(entries.length===1?'entry':'entries'):'';
    $('#saved-entries-empty').hidden=entries.length>0;
    $('#saved-entries-grid').replaceChildren(...entries.map(entry=>{
      const button=el('button',{type:'button',class:'saved-entry-card','aria-label':'Open '+entry.title},[
        el('div',{class:'saved-entry-thumb'},[el('img',{src:entry.image_url,alt:'',loading:'lazy'})]),
        el('div',{class:'saved-entry-card-info'},[
          el('span',{class:'saved-entry-date',text:formatDate(entry.date)}),el('h3',{text:entry.title}),
          el('p',{text:entry.page_count+' '+(entry.page_count===1?'page':'pages')+' · '+entry.sticker_count+' '+(entry.sticker_count===1?'sticker':'stickers')})
        ])
      ]);
      button.addEventListener('click',async()=>{try {openEntry(await bookApi('/entries/'+entry.id));} catch(e){error(e.message);}});
      return button;
    }));
  }
  function showPage() {
    if (!book.current) return;
    const page=book.current.pages[book.page];
    $('#entry-page-number').textContent='Page '+(book.page+1)+' of '+book.current.page_count;
    $('#previous-entry-page').disabled=book.page===0;
    $('#next-entry-page').disabled=book.page===book.current.page_count-1;
    $('#scrapbook-page-loading').hidden=false;
    const preview=$('#scrapbook-page-preview');
    preview.onload=()=>{$('#scrapbook-page-loading').hidden=true;};
    preview.onerror=()=>{$('#scrapbook-page-loading').textContent='Use the download link to open this page.';};
    preview.src=page.image_url;preview.alt=book.current.title+', page '+(book.page+1)+' of '+book.current.page_count;
    $('#entry-page-svg').href=page.svg_url+'?download=true';
    $('#entry-page-png').href=page.image_url+'?download=true';
  }
  function openEntry(entry,scroll=true) {
    book.current=entry;book.page=0;
    $('#saved-entry-title').textContent=entry.title;
    $('#entry-transcript-text').textContent=entry.text||'This entry tells its story with stickers.';
    $('#saved-entry-summary').textContent=formatDate(entry.date)+' · '+entry.page_count+' '+(entry.page_count===1?'page':'pages')+' · '+entry.sticker_count+' '+(entry.sticker_count===1?'sticker':'stickers');
    $('#entry-download-all').href=entry.download_url;
    $('#entry-viewer').hidden=false;showPage();
    history.replaceState(null,'','?entry='+entry.id+'#scrapbook');
    if (scroll) $('#entry-viewer').scrollIntoView({behavior:smooth(),block:'start'});
  }
  function clearDraft() {
    $('#entry-form').reset();$('#entry-date').value=today();book.selected.clear();renderPicker();
  }
  async function addEntry(event) {
    event.preventDefault();if(book.busy||$('#entry-add').disabled)return;
    $('#entry-error').hidden=true;setBusy(true);
    try {
      const entry=await bookApi('/entries',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
        title:$('#entry-title').value,text:$('#entry-text').value,date:$('#entry-date').value,sticker_ids:[...book.selected.keys()]
      })});
      openEntry(entry);clearDraft();await loadEntries();
      toast('Added to your scrapbook · '+entry.page_count+' '+(entry.page_count===1?'page':'pages'));
    } catch(e) {error(e.message);}
    finally {setBusy(false);}
  }
  async function refresh() {
    if (book.loading) return book.loading;
    book.loading=Promise.all([loadStickers(),loadEntries()]).catch(e=>error(e.message)).finally(()=>{book.loading=null;});
    return book.loading;
  }

  $('#entry-date').value=today();
  $('#entry-form').addEventListener('submit',addEntry);
  $('#entry-text').addEventListener('input',updateControls);
  $('#sticker-search').addEventListener('input',renderPicker);
  $('#sticker-source').addEventListener('change',renderPicker);
  $('#clear-sticker-selection').addEventListener('click',()=>{book.selected.clear();renderPicker();});
  $('#previous-entry-page').addEventListener('click',()=>{if(book.page>0){book.page--;showPage();}});
  $('#next-entry-page').addEventListener('click',()=>{if(book.current&&book.page<book.current.page_count-1){book.page++;showPage();}});
  $('#new-entry-button').addEventListener('click',()=>{clearDraft();history.replaceState(null,'',location.pathname+'#scrapbook');$('#entry-form').scrollIntoView({behavior:smooth(),block:'start'});$('#entry-title').focus({preventScroll:true});});
  window.addEventListener('scrapbook:open',refresh);
  window.addEventListener('scrapbook:stickers-updated',()=>{loadStickers().catch(e=>error(e.message));});
  window.addEventListener('scrapbook:pick',async event=>{
    if(book.busy){toast('Wait for your current entry to finish.');return;}
    try {
      await loadStickers();const item=book.catalog.find(candidate=>candidate.id===event.detail);
      if (!item) throw new Error('Refresh the page to choose this sticker.');
      if (book.selected.size>=50&&!book.selected.has(item.id)) throw new Error('You can use up to 50 stickers in one entry.');
      book.selected.set(item.id,item);renderPicker();location.hash='scrapbook';
      $('#entry-form').scrollIntoView({behavior:smooth(),block:'start'});toast(item.label+' selected for your entry.');
    } catch(e){error(e.message);}
  });
  refresh();
  const requested=new URLSearchParams(location.search).get('entry');
  if (/^[a-f0-9]{32}$/.test(requested||'')) bookApi('/entries/'+requested).then(entry=>openEntry(entry,false)).catch(e=>error(e.message));
})();
