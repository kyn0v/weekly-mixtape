"""Read-only inspection, or stage audio + a sample-accurate plan. No GUI edits."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.request

# Avoid generating caches containing this installation's absolute source paths.
sys.dont_write_bytecode = True
from audio_backend import load_preparer
from audio_contract import PreparedAudio, SAMPLE_RATE

PLAYLIST = '17400667938'
ROOT = Path.home() / 'Music' / 'GarageBand'
DOWNLOADS = Path.home() / 'Music' / '网易云音乐'
INTRO = Path(__file__).resolve().parent.parent / 'assets' / 'Intro.mp3'
RATE = SAMPLE_RATE


def expand_path(path):
    return Path(path).expanduser().absolute()


def portable_path(path):
    """Use ~/ for paths under the current home; keep other locations explicit."""
    path = expand_path(path)
    try:
        return str(Path('~') / path.relative_to(Path.home().absolute()))
    except ValueError:
        return str(path)


def next_project(root):
    root = expand_path(root)
    numbers = [int(p.stem) for p in root.iterdir()
               if p.is_dir() and re.fullmatch(r'\d+\.band', p.name)]
    return root / f'{max(numbers, default=0) + 1:03d}.band'


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def inspect(root, downloads):
    root, downloads = expand_path(root), expand_path(downloads)
    req = urllib.request.Request(
        f'https://music.163.com/api/playlist/detail?id={PLAYLIST}',
        headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://music.163.com/'})
    with urllib.request.urlopen(req, timeout=25) as response:
        data = json.load(response)
    p = data.get('result') or data.get('playlist') or {}
    tracks = p.get('tracks', [])
    if data.get('code') != 200 or not tracks or int(p.get('id', 0)) != int(PLAYLIST):
        raise ValueError('Playlist unavailable; inspect in browser, do not reuse stale order')
    if 'trackCount' not in p or p['trackCount'] != len(tracks):
        raise ValueError('Playlist count missing/incomplete; verify full order in browser')
    if p.get('trackIds') and [t['id'] for t in p['trackIds']] != [t['id'] for t in tracks]:
        raise ValueError('Playlist ID order differs; verify in browser')
    return {
        'playlist_id': PLAYLIST, 'fetched_at': datetime.now(timezone.utc).isoformat(),
        'name': p.get('name'), 'project': portable_path(next_project(root)),
        'tracks': [{'id': t['id'], 'title': t['name'],
                    'artists': [a['name'] for a in t.get('artists', t.get('ar', []))],
                    'album': (t.get('album') or t.get('al') or {}).get('name')}
                   for t in tracks],
        'files': [{'path': portable_path(f), 'bytes': f.stat().st_size,
                   'modified': f.stat().st_mtime}
                  for f in sorted(downloads.iterdir())
                  if f.is_file() and not f.name.startswith('.')]}


def prepare(selection, root, intro=INTRO):
    root = expand_path(root)
    if str(selection.get('playlist_id')) != PLAYLIST or not selection.get('tracks'):
        raise ValueError('Expected the fixed playlist ID and a nonempty ordered tracks list')
    tracks = selection['tracks']
    sources = [expand_path(intro)]
    names = ['IntroTrack']
    for i, row in enumerate(tracks, 1):
        if not row.get('id') or not row.get('title') or not isinstance(row.get('artists'), list) or not row['artists']:
            raise ValueError(f'Missing song identity in row {i}')
        source = Path(row['source']).expanduser()
        if not source.is_absolute():
            raise ValueError(f'Expected absolute or ~/ source path: {row["source"]}')
        sources.append(source)
        names.append(f'{i:02d} {", ".join(row["artists"])} - {row["title"]}')
    if len({p.resolve() for p in sources[1:]}) != len(sources[1:]):
        raise ValueError('Same source matched twice; clarify duplicate playlist entries first')
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(source)
    prepare_audio = load_preparer()
    project = next_project(root)
    assets = root / f'{project.stem}-mixtape-assets'
    assets.mkdir()  # exclusive reservation; leave partial results on error for diagnosis
    saved_selection = {**selection, 'tracks': [
        {**row, 'source': portable_path(source)}
        for row, source in zip(tracks, sources[1:])]}
    (assets / 'selection.json').write_text(json.dumps(saved_selection, ensure_ascii=False, indent=2))
    plan = {'playlist_id': PLAYLIST, 'created_at': datetime.now(timezone.utc).isoformat(),
            'path_base': 'plan-directory',
            'project': str(Path('..') / project.name), 'sample_rate': RATE, 'gap_frames': 60 * RATE,
            'status': 'prepared-not-imported',
            'tracks': [{'name': 'Vocal', 'type': 'empty-audio',
                        'monitoring': False, 'regions': []}]}
    cursor = 0
    for i, (source, name) in enumerate(zip(sources, names)):
        work = assets / f'{i:02d}'
        source_hash = sha256(source)
        prepared = prepare_audio(source, work)
        if not isinstance(prepared, PreparedAudio):
            raise TypeError('Audio module must return the public PreparedAudio type')
        prepared.validate(work)
        wav, samples = prepared.path, prepared.frame_count
        if sha256(source) != source_hash:
            raise RuntimeError(f'Source changed during preparation: {source}')
        repeats = 1 if i == 0 else 2
        regions = [{'start_frame': cursor + j * samples,
                    'end_frame': cursor + (j + 1) * samples,
                    'start_seconds': (cursor + j * samples) / RATE}
                   for j in range(repeats)]
        plan['tracks'].append({'name': name, 'source': portable_path(source), 'source_sha256': source_hash,
                               'wav': str(wav.relative_to(assets)), 'wav_sha256': sha256(wav),
                               'duration_frames': samples, 'regions': regions})
        cursor = regions[-1]['end_frame'] + 60 * RATE
    plan['end_frame'] = cursor - 60 * RATE
    plan['duration_seconds'] = plan['end_frame'] / RATE
    (assets / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2))
    return {'plan': portable_path(assets / 'plan.json'), 'project': portable_path(project),
            'tracks': len(plan['tracks']), 'regions': 1 + 2 * len(tracks),
            'duration_seconds': plan['duration_seconds']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['inspect', 'prepare'])
    p.add_argument('selection', nargs='?')
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--downloads', type=Path, default=DOWNLOADS)
    p.add_argument('--intro', type=Path, default=INTRO, help='Defaults to bundled assets/Intro.mp3')
    args = p.parse_args()
    if args.command == 'inspect':
        result = inspect(args.root, args.downloads)
    else:
        if not args.selection:
            p.error('prepare requires an ordered selection JSON file')
        result = prepare(json.loads(expand_path(args.selection).read_text()), args.root, args.intro)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
