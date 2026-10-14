"""Prepare a compact CC0 sky backdrop, keeping HDR lighting independent.

Call prepare_backdrop() in the existing Python environment. Original downloads
are held in memory; only the current web asset and its provenance are saved.
"""
from hashlib import md5, sha256
from io import BytesIO
import json
from pathlib import Path
from urllib.request import Request, urlopen
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / 'web/public/environment'
IDENTIFIER = 'kloppenheim_05_puresky'


def download(url):
    with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=50) as response:
        return response.read()


def prepare_backdrop():
    files = json.loads(download('https://api.polyhaven.com/files/' + IDENTIFIER))
    descriptor = files['tonemapped']
    original = download(descriptor['url'])
    assert len(original) == descriptor['size']
    assert md5(original).hexdigest() == descriptor['md5']
    image = Image.open(BytesIO(original)).convert('RGB')
    image = image.resize((2048, 1024), Image.Resampling.LANCZOS)
    output = DESTINATION / 'daylight-sky-2k.webp'
    image.save(output, format='WEBP', quality=83, method=6)
    content = output.read_bytes()
    assert len(content) < 250_000, 'Sky backdrop exceeds optional transfer budget'
    record = dict(path='/environment/' + output.name, name='Kloppenheim 05 (Pure Sky) backdrop',
                  authors=['Greg Zaal', 'Jarod Guest'], license='CC0-1.0',
                  source='https://polyhaven.com/a/' + IDENTIFIER,
                  licenseSource='https://polyhaven.com/license', download=descriptor['url'],
                  originalSha256=sha256(original).hexdigest(), sha256=sha256(content).hexdigest(),
                  bytes=len(content), dimensions=[2048, 1024],
                  scope='Static photographic sky backdrop; existing HDR supplies lighting. Not an LSE survey.')
    manifest_path = DESTINATION / 'sources.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['assets'] = [item for item in manifest['assets'] if item['path'] != record['path']] + [record]
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(path=record['path'], bytes=len(content))))
    return record


if __name__ == '__main__':
    prepare_backdrop()
