"""Reading and extending a Viwoods AiPaper `.note` archive.

The tablet accepts an archive only if the bytes it wrote are still exactly
where it left them. Recompressing an archive whose contents are byte for byte
identical is enough to have it refused as a damaged folder — measured against
`com.wisky.notewriter` 1.8.9. So nothing here rewrites an archive: entries are
appended after the originals, and only the central directory is rebuilt, which
is what a central directory is for.
"""

import json
import struct
import zlib


END_RECORD = 0x06054B50
CENTRAL_RECORD = 0x02014B50
LOCAL_RECORD = 0x04034B50
DESCRIPTOR = 0x08074B50
# Bit 3 puts sizes and CRC in a descriptor after the data, bit 11 marks the
# name as UTF-8: the two the tablet's own streamed writer sets.
STREAMED = 0x808
LAYER, STROKES = 1, 7


def _end_of_directory(data):
    for start in range(len(data) - 22, max(-1, len(data) - 65558), -1):
        if struct.unpack("<I", data[start:start + 4])[0] == END_RECORD:
            count, size, offset = struct.unpack("<HII", data[start + 10:start + 20])
            return offset, size, count
    raise ValueError("Archive sans répertoire central : ce n’est pas un carnet AiPaper.")


def append(source, target, entries):
    """Copy `source` to `target` byte for byte, adding (name, data) entries."""
    data = source.read_bytes()
    offset, size, count = _end_of_directory(data)
    body, records = bytearray(data[:offset]), bytearray(data[offset:offset + size])
    for name, payload in entries:
        raw = name.encode("utf-8")
        deflated = zlib.compressobj(9, zlib.DEFLATED, -15)
        blob = deflated.compress(payload) + deflated.flush()
        crc = zlib.crc32(payload) & 0xFFFFFFFF
        here = len(body)
        body += struct.pack("<IHHHHHIIIHH", LOCAL_RECORD, 20, STREAMED, 8,
                            0, 0x21, 0, 0, 0, len(raw), 0) + raw + blob
        body += struct.pack("<IIII", DESCRIPTOR, crc, len(blob), len(payload))
        records += struct.pack("<IHHHHHHIIIHHHHHII", CENTRAL_RECORD, 20, 20, STREAMED,
                               8, 0, 0x21, crc, len(blob), len(payload), len(raw),
                               0, 0, 0, 0, 0, here) + raw
        count += 1
    start = len(body)
    body += records
    body += struct.pack("<IHHHHIIH", END_RECORD, 0, 0, count, count,
                        len(records), start, 0)
    target.write_bytes(bytes(body))
    return count


def _metadata(archive, suffix):
    entry = next((name for name in archive.namelist() if name.endswith(suffix)), None)
    if entry is None:
        raise ValueError(f"Cette archive ne contient pas {suffix} : "
                         "elle ne vient pas d’un carnet AiPaper.")
    return json.loads(archive.read(entry))


def resources(archive):
    """{page number: {resource type: declared file name}} for a whole notebook.

    Every page declares a layer and a stroke file whether or not it was ever
    written on; only a written one ships the file. That is what makes grafting
    possible: the names are already chosen, and the tablet is never asked to
    accept a resource it has not itself announced.
    """
    order = {page["id"]: page["order"]
             for page in _metadata(archive, "PageListFileInfo.json")}
    found = {}
    for entry in _metadata(archive, "PageResource.json"):
        page = order.get(entry.get("pid"))
        if page is not None:
            found.setdefault(page + 1, {})[entry["resourceType"]] = entry["fileName"]
    return found


def template_entry(archive):
    """The archive member holding the PDF the notebook was written on."""
    found = [name for name in archive.namelist() if name.lower().endswith(".pdf")]
    if len(found) != 1:
        raise ValueError("Cette archive ne contient pas exactement un gabarit PDF : "
                         "elle ne vient pas d’un carnet AiPaper.")
    return found[0]
