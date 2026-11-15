"""Install a built wheel in isolation and exercise its generated project."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import tempfile
import venv
import zipfile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel', type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        for required in (
            'flaxon/py.typed',
            'flaxon/cli/starter/',
            'flaxon/cli/starters/api/',
            'flaxon/cli/starters/api-db/',
            'flaxon/cli/starters/web/',
            'flaxon/admin/templates/',
            'flaxon/admin/static/',
            'flaxon/openapi/assets/redoc/redoc.standalone.js',
            'flaxon/openapi/assets/redoc/LICENSE',
            'flaxon/openapi/assets/redoc/MANIFEST.json',
            'flaxon/openapi/assets/swagger_ui/swagger-ui-bundle.js',
            'flaxon/openapi/assets/swagger_ui/swagger-ui.css',
            'flaxon/openapi/assets/swagger_ui/LICENSE',
            'flaxon/openapi/assets/swagger_ui/NOTICE',
            'flaxon/openapi/assets/swagger_ui/MANIFEST.json',
        ):
            if not any(name.startswith(required) for name in names):
                raise RuntimeError(f'Missing packaged resource: {required}')
    with tempfile.TemporaryDirectory(prefix='flaxon-wheel-') as temporary:
        root = Path(temporary)
        environment = root / 'environment'
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ('Scripts/python.exe' if __import__('os').name == 'nt' else 'bin/python')
        def run(*arguments: str, cwd: Path = root) -> None:
            subprocess.run([str(python), *arguments], cwd=cwd, check=True, timeout=180)
        run('-m', 'pip', 'install', f'{wheel}[standard,admin]', 'httpx')
        run('-m', 'flaxon', 'new', 'release_smoke', '--no-venv')
        project = root / 'release_smoke'
        for command in ('check', 'makemigrations', 'migrate'):
            run('management.py', command, cwd=project)
        run('-c', '''
from importlib.metadata import version
import flaxon
from app import app
from flaxon.testing import TestClient
assert 'site-packages' in flaxon.__file__, flaxon.__file__
assert flaxon.__version__ == version('flaxon')
client = TestClient(app)
for path in ('/', '/api/welcome/status', '/_flaxon/ui/app.js',
             '/_flaxon/modules/welcome/ui/Welcome.js', '/admin/login'):
    response = client.get(path)
    assert response.status_code == 200, (path, response.status_code)
assert client.get('/admin').status_code == 401
from flaxon.openapi import redoc_asset_response, swagger_asset_response
assert len(redoc_asset_response().body) > 1_000_000, 'bundled ReDoc is missing or truncated'
swagger_js = swagger_asset_response('swagger-ui-bundle.js').body
assert len(swagger_js) > 1_000_000, 'bundled Swagger UI is missing or truncated'
print('Installed wheel and starter smoke passed')
''', cwd=project)


if __name__ == '__main__':
    main()
