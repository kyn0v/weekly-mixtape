"""Public orchestration tests use a fake preparer; no private code or FFmpeg."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave

FAKE_PREPARER = '''from pathlib import Path
import shutil
import wave
from audio_contract import PreparedAudio

def prepare_audio(source, output_dir):
    output_dir.mkdir(parents=True)
    target = output_dir / 'audio.wav'
    shutil.copyfile(source, target)
    with wave.open(str(target), 'rb') as f:
        return PreparedAudio(target, f.getframerate(), f.getnframes(), f.getnchannels())
'''


class PublicWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'repo'
        (self.repo / 'scripts').mkdir(parents=True)
        source = Path(__file__).resolve().parent
        for name in ('prepare.py', 'audio_contract.py', 'audio_backend.py'):
            shutil.copy2(source / name, self.repo / 'scripts' / name)
        self.root = self.base / 'projects'
        self.root.mkdir()
        (self.root / '026.band').mkdir()
        (self.root / '999.backup.band').mkdir()
        self.source = self.base / 'fixture.custom-format'
        with wave.open(str(self.source), 'wb') as f:
            f.setparams((2, 3, 44100, 0, 'NONE', 'not compressed'))
            f.writeframes(b'\0' * 4410 * 6)

    def run_prepare(self):
        selection = {'playlist_id': '17400667938', 'tracks': [
            {'id': 1, 'title': 'Fixture', 'artists': ['Test'], 'source': str(self.source)}]}
        selected = self.base / 'selection.json'
        selected.write_text(json.dumps(selection))
        return subprocess.run([sys.executable, '-B', str(self.repo / 'scripts/prepare.py'),
                               'prepare', str(selected), '--root', str(self.root),
                               '--intro', str(self.source)], capture_output=True, text=True)

    def install_fake(self, code=FAKE_PREPARER):
        package = self.repo / 'modules/audio-preparer/audio_preparer'
        package.mkdir(parents=True)
        (package / '__init__.py').write_text(code)

    def test_plan_is_format_agnostic(self):
        self.install_fake()
        result = self.run_prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        plan = json.loads(Path(output['plan']).expanduser().read_text())
        vocal, intro, song = plan['tracks']
        self.assertEqual((output['tracks'], output['regions']), (3, 3))
        self.assertEqual(vocal['name'], 'Vocal')
        self.assertEqual(vocal['regions'], [])
        self.assertEqual(plan['project'], '../027.band')
        self.assertEqual(song['wav'], '01/audio.wav')
        self.assertEqual(song['regions'][0]['start_frame'] - intro['regions'][0]['end_frame'], 60 * 44100)
        self.assertEqual(song['regions'][0]['end_frame'], song['regions'][1]['start_frame'])
        self.assertEqual(plan['end_frame'], song['regions'][1]['end_frame'])
        self.assertFalse((self.root / '027.band').exists())
        self.assertNotEqual(self.run_prepare().returncode, 0)

    def test_missing_backend_fails_before_staging(self):
        result = self.run_prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('git submodule update --init --recursive', result.stderr)
        self.assertFalse((self.root / '027-mixtape-assets').exists())

    def test_invalid_backend_result_rejected(self):
        self.install_fake(FAKE_PREPARER.replace('f.getframerate()', '48000'))
        result = self.run_prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('44100 Hz', result.stderr)
        self.assertFalse((self.root / '027-mixtape-assets/plan.json').exists())


if __name__ == '__main__':
    unittest.main()
