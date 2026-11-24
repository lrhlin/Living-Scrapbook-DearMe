"""Checks for Bob responses, sticker vectors and the local generation workflow."""
import asyncio
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
import xml.etree.ElementTree as ET

import httpx
from PIL import Image
from app.core.config import settings
from app.main import app
from app.services.bob_client import BobError, extract_json, parse_output
from app.services.svg_stickers import SVGError, build_sticker
from app.services import studio_jobs

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640"><defs><linearGradient id="fur"><stop offset="0" stop-color="#999"/><stop offset="1" stop-color="#777"/></linearGradient></defs><g id="artwork"><path d="M150 400L180 120L300 210L450 120L490 400Q320 590 150 400Z" fill="url(#fur)"/><path d="M180 340L80 320" fill="none" stroke="#333" stroke-width="2"/></g></svg>'


class ProviderAndVectorTests(unittest.TestCase):
    def test_streamed_json_ignores_tool_output_and_preserves_cost(self):
        text = '\n'.join(json.dumps(event) for event in [
            {"type":"message","role":"user","content":"not provider output"},
            {"type":"message","role":"assistant","content":"```json\n{\"objects\":"},
            {"type":"message","role":"assistant","content":"[]}\n```"},
            {"type":"result","status":"success","stats":{"session_costs":0.07}},
        ])
        message, usage = parse_output(text)
        self.assertEqual(extract_json(message), {"objects": []})
        self.assertEqual(usage["bobcoins"], 0.07)
        self.assertIsNone(usage["total_tokens"])
        self.assertEqual(extract_json('{"narrative":"A little memory."}'), {"narrative":"A little memory."})

    def test_limit_is_failure_even_when_cli_reports_success(self):
        text = '\n'.join(json.dumps(e) for e in [
            {"type":"error","message":"Maximum turns"},
            {"type":"result","status":"success","last_message":"incomplete"},
        ])
        with self.assertRaises(BobError):
            parse_output(text)

    def test_border_uses_the_whisker_geometry_and_preserves_original(self):
        raw, final = build_sticker(SVG)
        root = ET.fromstring(final)
        backing = next(e for e in root if e.get('id') == 'dearme-sticker-border')
        whisker = list(backing)[1]
        self.assertEqual(whisker.get('d'), 'M180 340L80 320')
        self.assertEqual(float(whisker.get('stroke-width')), 16)
        self.assertEqual(whisker.get('fill'), 'none')
        original = next(e for e in root if e.get('id') == 'artwork')
        self.assertEqual(list(original)[1].get('stroke'), '#333')
        self.assertNotIn('dearme-sticker-border', raw)

    def test_active_content_and_external_resources_are_rejected(self):
        bad = [SVG.replace('<defs>', '<script>alert(1)</script><defs>'),
               SVG.replace('fill="url(#fur)"', 'fill="url(https://example.com/image)"'),
               SVG.replace('<g id="artwork">', '<g id="artwork" onload="alert(1)">'),
               SVG.replace('<g id="artwork">', '<g>'),
               SVG.replace('id="fur"', 'id="artwork"'),
               '<!DOCTYPE svg [<!ENTITY x "bad">]>' + SVG]
        for sample in bad:
            with self.subTest(sample=sample[:70]), self.assertRaises(SVGError):
                build_sticker(sample)


class LocalPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = settings.upload_dir
        settings.upload_dir = self.temp.name
        self.ready = patch('app.api.v1.studio.status', return_value={"providers":{
            "openai":{"ready":True,"name":"OpenAI","key_file":"oaikey.txt"},
            "bob":{"ready":True,"name":"IBM Bob","key_file":"bobkey.txt"},
        }})
        self.ready.start()
        self.image = BytesIO()
        Image.new('RGB', (60, 40), '#888').save(self.image, format='JPEG')
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://local')

    async def asyncTearDown(self):
        await self.client.aclose()
        for task in list(studio_jobs._tasks):
            await task
        settings.upload_dir = self.previous
        self.ready.stop()
        self.temp.cleanup()

    async def test_upload_job_render_library_download_and_disk_reload(self):
        reply = {"objects":[{"label":"Cat head","description":"A simple portrait","svg":SVG}]}
        with patch('app.services.object_extractor.run_bob', new=AsyncMock(return_value=(reply, {"bobcoins":0.012,"total_tokens":None}))) as provider:
            response = await self.client.post('/api/v1/studio/jobs', files={"file":('cat.jpg',self.image.getvalue(),'image/jpeg')}, data={"subject":"Cat head only","style":"paper","count":"1","provider":"bob"})
            self.assertEqual(response.status_code, 202, response.text)
            job_id=response.json()['id']
            for _ in range(100):
                job=(await self.client.get('/api/v1/studio/jobs/'+job_id)).json()
                if job['status'] in {'done','error'}:
                    break
                await asyncio.sleep(0.05)
            self.assertEqual(job['status'], 'done', job)
            self.assertEqual(provider.await_count, 1)
        png=await self.client.get(job['result']['objects'][0]['image_url'])
        self.assertTrue(png.content.startswith(b'\x89PNG'))
        svg=await self.client.get(job['result']['objects'][0]['svg_url']+'?download=true')
        self.assertIn('attachment',svg.headers['content-disposition'])
        self.assertIn('sandbox',svg.headers['content-security-policy'])
        self.assertNotIn(job_id, studio_jobs._active)
        restored=studio_jobs.get_job(job_id)
        self.assertEqual(restored['result']['usage']['bobcoins'],0.012)
        self.assertEqual(len((await self.client.get('/api/v1/studio/jobs')).json()),1)

    async def test_invalid_upload_does_not_call_provider(self):
        with patch('app.services.object_extractor.run_bob',new=AsyncMock()) as provider:
            response=await self.client.post('/api/v1/studio/jobs',files={"file":('fake.png',b'not an image','image/png')})
            self.assertEqual(response.status_code,400)
            provider.assert_not_awaited()

    async def test_normalized_photo_has_no_original_exif(self):
        exif=Image.Exif()
        exif[270]='Private reference metadata'
        source=BytesIO()
        Image.new('RGB',(20,20)).save(source,format='JPEG',exif=exif)
        destination=Path(self.temp.name)/'normalized.png'
        studio_jobs.normalize_image(source.getvalue(),destination)
        with Image.open(destination) as image:
            self.assertNotIn(270,image.getexif())

    async def test_public_routes_never_serve_arbitrary_files(self):
        self.assertEqual((await self.client.get('/api/v1/studio/jobs/not-a-job/files/bobkey.txt')).status_code,404)
        self.assertEqual((await self.client.get('/api/v1/studio/jobs/not-a-job/files/oaikey.txt')).status_code,404)
        self.assertEqual((await self.client.get('/api/v1/studio/examples/cat/bobkey.txt')).status_code,404)
        home=await self.client.get('/')
        self.assertEqual(home.status_code,200)
        self.assertNotIn('BOB_API_KEY',home.text)


if __name__ == '__main__':
    unittest.main()
