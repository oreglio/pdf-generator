"""Build a macOS launcher using this checkout and its current Python environment."""

import argparse
import importlib.util
import plistlib
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def build(target):
    if sys.platform != 'darwin':
        raise RuntimeError('Ce lanceur nécessite macOS.')
    if target.exists():
        raise ValueError(f'{target} existe déjà. Choisissez un autre emplacement.')
    for module in ('nicegui', 'webview'):
        if importlib.util.find_spec(module) is None:
            raise RuntimeError('Installez les dépendances avec pip install -r requirements-native.txt.')
    python = Path(sys.executable).absolute()
    icon = ROOT / 'assets/app/folio.png'
    with tempfile.TemporaryDirectory(prefix='folio-build-') as temporary:
        bundle = Path(temporary) / 'Folio.app'
        contents = bundle / 'Contents'
        resources = contents / 'Resources'
        executables = contents / 'MacOS'
        resources.mkdir(parents=True)
        executables.mkdir()
        iconset = Path(temporary) / 'Folio.iconset'
        iconset.mkdir()
        for size in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                suffix = '@2x' if scale == 2 else ''
                destination = iconset / f'icon_{size}x{size}{suffix}.png'
                subprocess.run(['sips', '-z', str(size * scale), str(size * scale),
                                str(icon), '--out', str(destination)], check=True,
                               stdout=subprocess.DEVNULL)
        subprocess.run(['iconutil', '-c', 'icns', str(iconset), '-o',
                        str(resources / 'Folio.icns')], check=True)
        info = {
            'CFBundleName': 'Folio', 'CFBundleDisplayName': 'Folio',
            'CFBundleIdentifier': 'app.readtoken.folio.local',
            'CFBundleExecutable': 'Folio', 'CFBundleIconFile': 'Folio.icns',
            'CFBundlePackageType': 'APPL', 'CFBundleVersion': '1',
            'CFBundleShortVersionString': '1.0', 'LSUIElement': True,
            'NSHighResolutionCapable': True,
        }
        (contents / 'Info.plist').write_bytes(plistlib.dumps(info))
        launcher = executables / 'Folio'
        launcher.write_text(f'''#!/bin/zsh
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
mkdir -p "$HOME/Library/Logs/Folio"
if [[ ! -x {shlex.quote(str(python))} || ! -f {shlex.quote(str(ROOT / 'macos_launcher.py'))} ]]; then
    /usr/bin/osascript -e 'display alert "Folio" message "Le projet ou son environnement Python a été déplacé. Reconstruisez le lanceur depuis le projet." as critical'
    exit 1
fi
cd {shlex.quote(str(ROOT))} || exit 1
{shlex.quote(str(python))} {shlex.quote(str(ROOT / 'macos_launcher.py'))} >> "$HOME/Library/Logs/Folio/app.log" 2>&1
if [[ $? -ne 0 ]]; then
    /usr/bin/osascript -e 'display alert "Folio" message "Impossible de démarrer. Consultez Library/Logs/Folio/app.log dans votre dossier personnel." as critical'
    exit 1
fi
''')
        launcher.chmod(0o755)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(bundle, target)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/Folio.app')
    args = parser.parse_args()
    try:
        print(build(args.output.expanduser().absolute()))
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')
