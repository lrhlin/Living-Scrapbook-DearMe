"""Provider routing, image-edit requests and raster scrapbook exports."""
import asyncio
import base64
from io import BytesIO
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from PIL import Image, ImageDraw

from app.core.config import settings
from app.main import app
from app.services import studio_jobs
from app.services.openai_stickers import OpenAIError, edit_image


class RasterStickerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.previous=settings.upload_dir
        settings.upload_dir=self.temp.name
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://local')
        image=Image.new('RGBA',(128,128),(0,0,0,0))
        ImageDraw.Draw(image).ellipse((20,20,108,108),fill='#ef2525')
        stream=BytesIO()
        image.save(stream,format='PNG')
        self.png=stream.getvalue()

    async def asyncTearDown(self):
        await self.client.aclose()
        for task in list(studio_jobs._tasks): await task
        settings.upload_dir=self.previous
        self.temp.cleanup()

    async def test_default_openai_job_download_and_scrapbook_export(self):
        calls=[]
        async def handle(request):
            calls.append(request)
            self.assertEqual(str(request.url),'https://api.openai.com/v1/images/edits')
            self.assertEqual(request.headers['Authorization'],'Bearer test-openai-key')
            body=await request.aread()
            for value in [settings.openai_image_model.encode(),b'transparent',b'reference.png',b'\x89PNG']:
                self.assertIn(value,body)
            return httpx.Response(200,json={'data':[{'b64_json':base64.b64encode(self.png).decode()}],
                                           'usage':{'input_tokens':20,'output_tokens':100,'total_tokens':120}})
        image_client=httpx.AsyncClient(transport=httpx.MockTransport(handle))
        with patch.object(type(settings),'read_openai_key',return_value='test-openai-key'), \
             patch('app.services.openai_stickers.httpx.AsyncClient',return_value=image_client), \
             patch('app.services.object_extractor.run_bob',new=AsyncMock()) as bob:
            response=await self.client.post('/api/v1/studio/jobs',files={'file':('pet.png',self.png,'image/png')},
                                            data={'subject':'Cat portrait','style':'soft'})
            self.assertEqual(response.status_code,202,response.text)
            job_id=response.json()['id']
            for _ in range(100):
                job=(await self.client.get('/api/v1/studio/jobs/'+job_id)).json()
                if job['status'] in {'done','error'}: break
                await asyncio.sleep(0.02)
            self.assertEqual(job['status'],'done',job)
            bob.assert_not_awaited()
        self.assertEqual(len(calls),1)
        self.assertEqual(job['provider'],'openai')
        sticker=job['result']['objects'][0]
        self.assertEqual(sticker['format'],'png')
        self.assertEqual(sticker['svg_url'],'')
        self.assertEqual(job['result']['usage']['total_tokens'],120)
        download=await self.client.get(sticker['image_url']+'?download=true')
        self.assertIn('attachment',download.headers['content-disposition'])
        with Image.open(BytesIO(download.content)) as image:
            self.assertEqual(image.getpixel((0,0))[3],0)
        entry_response=await self.client.post('/api/v1/scrapbook/entries',json={
            'title':'A raster keepsake','text':'An illustrated memory.','date':'2026-11-23',
            'sticker_ids':[f'job:{job_id}:0'],'theme':'cozy',
        })
        self.assertEqual(entry_response.status_code,201,entry_response.text)
        entry=entry_response.json()
        svg=(await self.client.get(entry['pages'][0]['svg_url'])).text
        self.assertIn('data:image/png;base64,',svg)
        rendered=await self.client.get(entry['pages'][0]['image_url'])
        with Image.open(BytesIO(rendered.content)) as image:
            colors=image.convert('RGB').getdata()
            self.assertTrue(any(r>200 and g<80 and b<80 for r,g,b in colors))
        shutil.rmtree(Path(settings.upload_dir)/'studio'/job_id)
        self.assertEqual((await self.client.get(entry['pages'][0]['image_url'])).status_code,200)
        self.assertTrue((Path(settings.upload_dir)/'scrapbook'/entry['id']/'sticker-0.png').is_file())
        self.assertNotIn('test-openai-key',json.dumps(studio_jobs.list_jobs()))

    async def test_provider_readiness_and_key_files_stay_private(self):
        with patch.object(type(settings),'read_openai_key',return_value='test-openai-key'), \
             patch.object(type(settings),'read_bob_key',return_value='test-bob-key'):
            status=(await self.client.get('/api/v1/studio/status')).json()
        self.assertEqual(status['default_provider'],'openai')
        self.assertTrue(status['providers']['openai']['ready'])
        self.assertEqual(status['providers']['bob']['key_file'],'bobkey.txt')
        self.assertNotIn('test-openai-key',json.dumps(status))
        self.assertNotIn('test-bob-key',json.dumps(status))
        with patch.object(type(settings),'read_openai_key',return_value=''), \
             patch('app.services.openai_stickers.edit_image',new=AsyncMock()) as provider:
            response=await self.client.post('/api/v1/studio/jobs',files={'file':('pet.png',self.png,'image/png')})
            self.assertEqual(response.status_code,503)
            provider.assert_not_awaited()
        invalid=await self.client.post('/api/v1/studio/jobs',files={'file':('pet.png',self.png,'image/png')},data={'provider':'other'})
        self.assertEqual(invalid.status_code,400)

    async def test_image_api_error_has_an_actionable_message(self):
        reference=Path(self.temp.name)/'reference.png'
        reference.write_bytes(self.png)
        image_client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(429,json={
            'error':{'message':'quota test-openai-key'},
        })))
        with patch.object(type(settings),'read_openai_key',return_value='test-openai-key'), \
             patch('app.services.openai_stickers.httpx.AsyncClient',return_value=image_client):
            with self.assertRaises(OpenAIError) as caught:
                await edit_image(reference,'A sticker',1)
        self.assertIn('credit balance',str(caught.exception))
        self.assertNotIn('test-openai-key',str(caught.exception))
