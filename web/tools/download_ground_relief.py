"""Pack verified CC0 ground height and roughness into small linear-data textures.

Run this file in the existing Python environment. Source bytes are verified
before conversion; the original survey geometry and palette remain unchanged.
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


def download(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=40) as response:
        return response.read()


def prepare_ground_relief():
    manifest_path = DESTINATION / 'sources.json'
    manifest = json.loads(manifest_path.read_text())
    records = []
    for identifier, kind, metres in ASSETS:
        files = json.loads(download(f'https://api.polyhaven.com/files/{identifier}'))
        channels, originals = [], []
        for channel, asset_type in [('red', 'Displacement'), ('green', 'Rough')]:
            descriptor = files[asset_type]['1k']['jpg']
            content = download(descriptor['url'])
            assert len(content) == descriptor['size']
            assert hashlib.md5(content).hexdigest() == descriptor['md5']
            channels.append(Image.open(BytesIO(content)).convert('L').resize((512, 512), Image.Resampling.LANCZOS))
            originals.append(dict(channel=channel, semantic=asset_type, download=descriptor['url'],
                                  originalSha256=hashlib.sha256(content).hexdigest(), bytes=len(content)))
        # Five-bit asphalt data is sufficient for millimetre relief and roughness.
        # Quantize before lossless packing to avoid spending bandwidth on sensor noise.
        if kind == 'asphalt':
            channels = [channel.point(lambda value: round(round(value * 31 / 255) * 255 / 31)) for channel in channels]
        packed = Image.merge('RGB', (*channels, Image.new('L', (512, 512))))
        output = DESTINATION / f'{kind}-relief-512.webp'
        packed.save(output, format='WEBP', lossless=True, method=6)
        assert Image.open(output).convert('RGB').tobytes() == packed.tobytes()
        content = output.read_bytes()
        base = next(record for record in manifest['assets'] if record['path'] == f'/environment/{kind}-finish-512.webp')
        records.append(dict(path='/environment/' + output.name, name=base['name'] + ' surface data',
                            authors=base['authors'], license='CC0-1.0', source=base['source'], originals=originals,
                            sha256=hashlib.sha256(content).hexdigest(), bytes=len(content), dimensions=[512, 512],
                            repeatMetres=metres, channels=dict(red='height', green='roughness', blue='unused'),
                            colorSpace='linear-data', precisionBits=5 if kind == 'asphalt' else 8, scope='Presentation relief only. Not an LSE survey.'))
    paths = {record['path'] for record in records}
    manifest['assets'] = [record for record in manifest['assets'] if record['path'] not in paths] + records
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps([dict(path=record['path'], bytes=record['bytes']) for record in records]))


if __name__ == '__main__':
    prepare_ground_relief()
