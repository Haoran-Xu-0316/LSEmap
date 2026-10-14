"""Fetch the fixed CC0 daylight panorama; callable with download_daylight()."""
from hashlib import md5, sha256
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / 'web/public/environment/kloppenheim-daylight-1k.hdr'
DOWNLOAD = 'https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/1k/kloppenheim_05_puresky_1k.hdr'
EXPECTED_MD5 = 'fe0d85219b08932d0467c3752012b749'


def download_daylight():
    request = Request(DOWNLOAD, headers={'User-Agent': 'LSEmap/198 CC0 daylight asset'})
    with urlopen(request, timeout=60) as response:
        pixels = response.read(2_000_001)
    assert len(pixels) <= 2_000_000, 'Optional panorama exceeds the delivery budget'
    assert md5(pixels).hexdigest() == EXPECTED_MD5, 'Poly Haven 1k checksum mismatch'
    assert b'-Y 512 +X 1024' in pixels[:300], 'Unexpected panorama dimensions'
    DESTINATION.write_bytes(pixels)
    source = {
        'path': '/environment/kloppenheim-daylight-1k.hdr',
        'name': 'Kloppenheim 05 (Pure Sky)',
        'authors': ['Greg Zaal', 'Jarod Guest'],
        'license': 'CC0-1.0',
        'licenseSource': 'https://polyhaven.com/license',
        'source': 'https://polyhaven.com/a/kloppenheim_05_puresky',
        'download': DOWNLOAD,
        'sha256': sha256(pixels).hexdigest(),
        'bytes': len(pixels), 'dimensions': [1024, 512],
        'scope': 'Presentation sky and daylight reflections. Not an LSE site survey.',
    }
    proof = ROOT / 'result/blender/daylight198'
    proof.mkdir(parents=True, exist_ok=True)
    (proof / 'source.json').write_text(json.dumps(source, indent=2) + '\n')
    print(json.dumps(source))
    return source


if __name__ == '__main__':
    download_daylight()
