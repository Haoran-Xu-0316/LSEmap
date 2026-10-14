"""Prepare two small CC0 ground finishes from verified Poly Haven originals.

Fixed project paths keep this usable in the existing Python environment.
The texture tones are presentation finishes, never an LSE surface survey.
"""
from pathlib import Path
from io import BytesIO
import hashlib
import json
import urllib.request
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / 'web/public/environment'
ASSETS = [('asphalt_02', 'asphalt', 3), ('concrete_floor_02', 'stone', 2)]


def read_url(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=40) as response:
        return response.read()


def prepare_assets():
    manifest_path = DESTINATION / 'sources.json'
    manifest = json.loads(manifest_path.read_text())
    records = []
    for identifier, kind, metres in ASSETS:
        metadata = json.loads(read_url(f'https://api.polyhaven.com/info/{identifier}'))
        files = json.loads(read_url(f'https://api.polyhaven.com/files/{identifier}'))
        source = files['Diffuse']['1k']['jpg']
        original = read_url(source['url'])
        assert len(original) == source['size']
        assert hashlib.md5(original).hexdigest() == source['md5']
        image = Image.open(BytesIO(original)).convert('RGB')
        image.thumbnail((512, 512), Image.Resampling.LANCZOS)
        output = DESTINATION / f'{kind}-finish-512.webp'
        image.save(output, format='WEBP', quality=74 if kind == 'asphalt' else 78, method=6)
        pixels = Image.open(output).convert('RGB')
        linear = lambda c: c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
        luminance = sum(sum(linear(c / 255) * w for c, w in zip(pixel, (.2126, .7152, .0722)))
                        for pixel in pixels.getdata()) / (pixels.width * pixels.height)
        content = output.read_bytes()
        records.append(dict(path='/environment/' + output.name, name=metadata['name'],
                            authors=list(metadata['authors']), license='CC0-1.0',
                            source='https://polyhaven.com/a/' + identifier,
                            download=source['url'], originalSha256=hashlib.sha256(original).hexdigest(),
                            sha256=hashlib.sha256(content).hexdigest(), bytes=len(content),
                            dimensions=list(pixels.size), repeatMetres=metres,
                            linearLuminanceMean=round(luminance, 6),
                            scope='Shared ground finish only; geometry, joints and recorded palette remain authored. Not an LSE survey.'))
    paths = {item['path'] for item in records}
    manifest['assets'] = [item for item in manifest['assets'] if item['path'] not in paths] + records
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(records, indent=2))


if __name__ == '__main__':
    prepare_assets()
