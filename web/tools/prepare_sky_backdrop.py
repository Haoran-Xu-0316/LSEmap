"""Prepare one verified CC0 cloudy sky and its compact matching backdrop.

Use the existing Python environment. Source downloads stay in memory; current
web assets and source hashes are saved, with no original JPG backup copies.
"""
from hashlib import md5, sha256
from io import BytesIO
import json
from pathlib import Path
from urllib.request import Request, urlopen
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / 'web/public/environment'
IDENTIFIER = 'kloofendal_48d_partly_cloudy_puresky'


def download(url):
    with urlopen(Request(url, headers={'User-Agent': 'LSEmap asset preparation'}), timeout=50) as response:
        return response.read()


def verified_download(descriptor):
    content = download(descriptor['url'])
    assert len(content) == descriptor['size']
    assert md5(content).hexdigest() == descriptor['md5']
    return content


def prepare_backdrop():
    files = json.loads(download('https://api.polyhaven.com/files/' + IDENTIFIER))
    records = []
    common = dict(authors=['Greg Zaal', 'Jarod Guest'], license='CC0-1.0',
                  source='https://polyhaven.com/a/' + IDENTIFIER,
                  licenseSource='https://polyhaven.com/license',
                  scope='Presentation daylight and clouds, not an LSE weather record or survey.')
    hdr_descriptor = files['hdri']['1k']['hdr']
    hdr = verified_download(hdr_descriptor)
    assert len(hdr) < 2_000_000
    hdr_path = DESTINATION / 'daylight-1k.hdr'
    hdr_path.write_bytes(hdr)
    records.append(dict(common, path='/environment/' + hdr_path.name,
                        name='Kloofendal 48d Partly Cloudy (Pure Sky)',
                        download=hdr_descriptor['url'], sha256=sha256(hdr).hexdigest(),
                        bytes=len(hdr), dimensions=[1024, 512]))
    descriptor = files['tonemapped']
    original = verified_download(descriptor)
    image = Image.open(BytesIO(original)).convert('RGB').resize((2048, 1024), Image.Resampling.LANCZOS)
    output = DESTINATION / 'daylight-sky-2k.webp'
    image.save(output, format='WEBP', quality=83, method=6)
    content = output.read_bytes()
    assert len(content) < 100_000, 'Cloudy sky exceeds optional transfer budget'
    records.append(dict(common, path='/environment/' + output.name,
                        name='Kloofendal 48d Partly Cloudy backdrop', download=descriptor['url'],
                        originalSha256=sha256(original).hexdigest(), sha256=sha256(content).hexdigest(),
                        bytes=len(content), dimensions=[2048, 1024]))
    manifest_path = DESTINATION / 'sources.json'
    manifest = json.loads(manifest_path.read_text())
    replaced = {record['path'] for record in records} | {'/environment/kloppenheim-daylight-1k.hdr'}
    manifest['assets'] = [item for item in manifest['assets'] if item['path'] not in replaced] + records
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps([dict(path=record['path'], bytes=record['bytes']) for record in records]))
    return records


if __name__ == '__main__':
    prepare_backdrop()
