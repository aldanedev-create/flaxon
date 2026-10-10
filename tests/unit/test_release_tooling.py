"""Release commands must validate artifacts and preserve dry-run behavior."""
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

from flaxon.application.configuration import Config

ROOT = Path(__file__).resolve().parents[2]


def script(name):
    return runpy.run_path(str(ROOT / 'scripts' / name))


@pytest.mark.parametrize('secret', ['12345678901234567890123456789012', 'true', 'a,b,c'])
def test_environment_secrets_remain_exact_strings(monkeypatch, secret):
    monkeypatch.setenv('FLAXON_SECRET_KEY', secret)
    assert Config().get_secret_key() == secret


@pytest.mark.parametrize('heading', ['## Unreleased', '## [Unreleased]'])
def test_release_changelog_preserves_history(tmp_path, monkeypatch, heading):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / 'CHANGELOG.md'
    path.write_text(f'# Changelog\n\n{heading}\n\n- New change\n\n## [0.2.7]\n\n- Previous change\n')
    script('release.py')['update_changelog']('0.3.0')
    text = path.read_text()
    assert '## [Unreleased]' in text
    assert '## [0.3.0] - ' in text
    assert '- New change' in text
    assert '## [0.2.7]\n\n- Previous change' in text


def test_missing_changelog_section_fails(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path('CHANGELOG.md').write_text('# No release section\n')
    with pytest.raises(ValueError):
        script('release.py')['update_changelog']('0.3.0')


@pytest.mark.parametrize('name, function', [('build.py', 'check_dist'), ('release.py', 'publish_to_pypi'), ('release.py', 'publish_to_testpypi')])
def test_artifact_commands_use_real_paths(tmp_path, monkeypatch, name, function):
    monkeypatch.chdir(tmp_path)
    Path('dist').mkdir()
    for filename in ['flaxon.whl', 'flaxon.tar.gz', 'unrelated.txt']:
        Path('dist', filename).write_bytes(b'test')
    calls = []
    def run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr('subprocess.run', run)
    script(name)[function]()
    args, kwargs = calls[0]
    assert 'dist/flaxon.whl' in args and 'dist/flaxon.tar.gz' in args
    assert 'dist/unrelated.txt' not in args and 'dist/*' not in args
    assert not kwargs.get('shell')


def test_release_dry_run_performs_no_subprocesses(monkeypatch):
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr('sys.argv', ['release.py', '0.3.0', '--dry-run'])
    def unexpected(*args, **kwargs):
        pytest.fail('Dry-run must not execute build, tag or upload')
    monkeypatch.setattr('subprocess.run', unexpected)
    before = [(path, path.read_bytes()) for path in [ROOT / 'CHANGELOG.md', ROOT / 'src/flaxon/version.py']]
    script('release.py')['main']()
    assert all(path.read_bytes() == content for path, content in before)


def test_release_updates_authoritative_version(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = Path('src/flaxon/version.py')
    path.parent.mkdir(parents=True)
    path.write_text('__version__ = "0.2.7"\n')
    commands = script('release.py')
    assert commands['get_current_version']() == '0.2.7'
    commands['update_version']('0.3.0')
    assert commands['get_current_version']() == '0.3.0'


@pytest.mark.parametrize('version', ['0.3.0', '0.3.0rc1', '0.3.0a1', '0.3.0b2', '0.3.0.dev1'])
def test_version_module_imports_release_candidates(version):
    source = (ROOT / 'src/flaxon/version.py').read_text().replace('__version__ = "0.2.7"', f'__version__ = "{version}"')
    namespace = {}
    exec(compile(source, 'version.py', 'exec'), namespace)
    assert namespace['__version_info__'] == (0, 3, 0)
    assert namespace['is_release']() is (version == '0.3.0')


def test_release_commit_stages_only_version_and_changelog(monkeypatch):
    calls = []
    monkeypatch.setattr('subprocess.run', lambda args, **kwargs: calls.append(args))
    script('release.py')['commit_release']('0.3.0')
    assert calls == [['git', 'add', 'src/flaxon/version.py', 'CHANGELOG.md'],
                     ['git', 'commit', '-m', 'Release 0.3.0']]


def test_ci_compiler_constraint_is_shared_with_isolated_wheel_install():
    import re

    constraint = (ROOT / "requirements/ci.txt").read_text()
    match = re.search(r"teloce-py @ git\+https://github.com/aldanedev-create/teloce-py.git@([0-9a-f]{40})", constraint)
    assert match, "Pin compiler source to an immutable commit"
    for filename in ("orm.yml", "fullstack.yml"):
        workflow = (ROOT / ".github/workflows" / filename).read_text()
        assert "PIP_CONSTRAINT: ${{ github.workspace }}/requirements/ci.txt" in workflow
    assert match.group(1) in (ROOT / ".github/workflows/fullstack.yml").read_text()
