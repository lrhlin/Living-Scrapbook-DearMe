import asyncio
from datetime import date
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from zipfile import ZipFile
from io import BytesIO
import xml.etree.ElementTree as ET

import httpx

from app.core.config import settings
from app.main import app
from app.services import scrapbook

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><defs><linearGradient id="same-paint"><stop offset="0" stop-color="#597658"/><stop offset="1" stop-color="#ced8b4"/></linearGradient></defs><g id="artwork"><circle cx="320" cy="320" r="220" fill="url(#same-paint)"/></g></svg>'


class PaginationTests(unittest.TestCase):
    def test_long_text_and_stickers_continue_without_loss_or_overlap(self):
        text=('A quiet afternoon with familiar faces, a cup of tea, and a story worth keeping. ' * 140)
        pages=scrapbook.paginate('The little moments',text,13)
        self.assertGreater(len(pages),1)
        lines=[]
        stickers=[]
        for page in pages:
            bottom=0
            for block in page['blocks']:
                self.assertGreaterEqual(block['y'],bottom)
                bottom=block['y']+block['height']
                self.assertLessEqual(bottom,scrapbook.BOTTOM)
                if block['type']=='text': lines.extend(block['lines'])
                else: stickers.extend(block['indices'])
        self.assertEqual(' '.join(lines).split(),text.split())
        self.assertEqual(stickers,list(range(13)))

    def test_long_unbroken_words_and_wide_characters_wrap(self):
        text='W'*600+'猫'*100
        lines=scrapbook.wrap_text(text,740)
        self.assertEqual(''.join(lines),text)
        self.assertTrue(all(scrapbook.text_width(line)<=740 for line in lines))

    def test_sticker_rows_do_not_interrupt_short_paragraphs(self):
        paragraph='A small memory can make an ordinary afternoon feel special. ' * 5
        pages=scrapbook.paginate('Little things',paragraph+'\n\n'+paragraph,3)
        chunks=[block['lines'] for page in pages for block in page['blocks'] if block['type']=='text']
        expected=scrapbook.wrap_text(paragraph,744)
        self.assertTrue(all([line for line in chunk if line]==expected for chunk in chunks))


class SavedScrapbookTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.previous=settings.upload_dir
        settings.upload_dir=self.temp.name
        self.job_id='a'*32
        self.job=Path(self.temp.name)/'studio'/self.job_id
        self.job.mkdir(parents=True)
        for index in range(2): (self.job/f'sticker-{index}.svg').write_text(SVG)
        (self.job/'job.json').write_text(json.dumps({
            'id':self.job_id,'status':'done','result':{'objects':[
                {'label':'A familiar face','image_url':'/image-0.png'},
                {'label':'A favorite place','image_url':'/image-1.png'},
            ]},
        }))
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://local')

    async def asyncTearDown(self):
        await self.client.aclose()
        settings.upload_dir=self.previous
        self.temp.cleanup()

    async def test_create_render_paginate_and_reopen_without_ai_or_source_files(self):
        text=('An afternoon to remember, with little details that made the day feel special. '*55)+'\n\n<never executable> & always a memory.'
        payload={'title':'A little story & its places','text':text,'date':'2026-11-22',
                 'sticker_ids':[f'job:{self.job_id}:0',f'job:{self.job_id}:1']}
        with patch('app.services.bob_client.run_bob',new=AsyncMock()) as ai:
            response=await self.client.post('/api/v1/scrapbook/entries',json=payload)
            self.assertEqual(response.status_code,201,response.text)
            ai.assert_not_awaited()
        entry=response.json()
        self.assertGreater(entry['page_count'],1)
        self.assertEqual(entry['sticker_count'],2)
        all_ids=[]
        references=[]
        for page in entry['pages']:
            svg_response=await self.client.get(page['svg_url'])
            self.assertEqual(svg_response.status_code,200)
            root=ET.fromstring(svg_response.text)
            ids=[e.get('id') for e in root.iter() if e.get('id')]
            self.assertEqual(len(ids),len(set(ids)))
            for e in root.iter():
                self.assertFalse(e.tag.endswith('script'))
                for value in e.attrib.values(): references.extend(re.findall(r'url\(#([^)]*)\)',value))
            all_ids.extend(ids)
            png=await self.client.get(page['image_url'])
            self.assertTrue(png.content.startswith(b'\x89PNG'))
        self.assertTrue(set(references)<=set(all_ids))
        # The entry has its own sticker snapshots and completed page exports.
        shutil.rmtree(self.job)
        reopened=(await self.client.get('/api/v1/scrapbook/entries/'+entry['id'])).json()
        self.assertEqual(reopened['text'],text)
        self.assertEqual(reopened['page_count'],entry['page_count'])
        archive=await self.client.get(entry['download_url'])
        with ZipFile(BytesIO(archive.content)) as bundle:
            self.assertEqual(len([n for n in bundle.namelist() if n.endswith('.png')]),entry['page_count'])
            self.assertIn(text,bundle.read('entry.txt').decode())
        listing=(await self.client.get('/api/v1/scrapbook/entries')).json()
        self.assertEqual(listing[0]['id'],entry['id'])
        self.assertEqual((await self.client.get(entry['pages'][0]['image_url'])).status_code,200)

    async def test_text_only_entry_and_validation(self):
        response=await self.client.post('/api/v1/scrapbook/entries',json={
            'title':'A quiet day','text':'Some stories only need words.','date':'2026-11-22','sticker_ids':[]})
        self.assertEqual(response.status_code,201,response.text)
        self.assertEqual(response.json()['page_count'],1)
        for payload in [
            {'text':'  ','sticker_ids':[]},
            {'text':'A memory','sticker_ids':['../../bobkey.txt']},
        ]:
            response=await self.client.post('/api/v1/scrapbook/entries',json={'date':'2026-11-22',**payload})
            self.assertEqual(response.status_code,400,response.text)
        response=await self.client.post('/api/v1/scrapbook/entries',json={'date':'2026-11-22','text':'unsafe\u0000text'})
        self.assertEqual(response.status_code,422)

    async def test_catalog_and_file_route_do_not_accept_user_paths(self):
        catalog=(await self.client.get('/api/v1/scrapbook/stickers')).json()
        self.assertIn(f'job:{self.job_id}:0',[item['id'] for item in catalog])
        self.assertEqual((await self.client.get('/api/v1/scrapbook/entries/'+self.job_id+'/files/bobkey.txt')).status_code,404)
        self.assertEqual((await self.client.get('/api/v1/scrapbook/entries/not-a-real-id')).status_code,404)


if __name__=='__main__': unittest.main()
