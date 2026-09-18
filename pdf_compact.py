"""Repack a finished PDF so a slow reader has less to parse.

A notebook of 2 388 pages carries some ninety thousand link annotations, each
a separate object with its own header and an uncompressed dictionary. The
format has had an answer since 1.5: object streams, which pack many small
objects into one compressed stream. On a real notebook that is 29,7 MB down to
10,2 — the same document, stored differently.

Nothing about the page is touched. Content streams stay byte for byte what
they were, every link and bookmark survives, and the rendering is identical to
the pixel. What changes is the version stamp, 1.4 to 1.5, and where the objects
live.

This is deliberately not a setting of the notebook: it describes how the file
is stored, not what is drawn on it, and it leaves the published notebooks alone
unless it is asked for.
"""

import shutil
import subprocess
from pathlib import Path


TOOL = "qpdf"
MISSING = ("qpdf est introuvable : le carnet est produit sans compactage. "
           "Installez-le (brew install qpdf, ou apt install qpdf) pour des "
           "fichiers deux à trois fois plus légers.")


def available():
    return shutil.which(TOOL) is not None


def compact(data, report=print, linearize=False):
    """The same document, repacked. Returns the original on any difficulty.

    `linearize` also puts the first page and a lookup table up front, so a
    reader can show page two thousand without walking the whole file. It costs
    a couple of megabytes back, and only pays off where the reader knows to use
    it — off by default.
    """
    if not available():
        report(MISSING)
        return data
    import tempfile
    with tempfile.TemporaryDirectory() as folder:
        source, target = Path(folder) / "in.pdf", Path(folder) / "out.pdf"
        source.write_bytes(data)
        command = [TOOL, "--object-streams=generate"]
        if linearize:
            command.append("--linearize")
        command += [str(source), str(target)]
        try:
            subprocess.run(command, capture_output=True, check=True, timeout=600)
            packed = target.read_bytes()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as error:
            report(f"Compactage impossible, le carnet reste tel quel : {error}")
            return data
    if not packed.startswith(b"%PDF") or len(packed) >= len(data):
        report("Compactage sans effet, le carnet reste tel quel.")
        return data
    report(f"Compacté : {len(data) / 1e6:.1f} Mo → {len(packed) / 1e6:.1f} Mo "
           f"({100 * (1 - len(packed) / len(data)):.0f} % de moins à lire).")
    return packed
