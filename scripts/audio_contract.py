"""Public boundary: one source in, one verified GarageBand-compatible WAV out."""
from dataclasses import dataclass
from pathlib import Path

SAMPLE_RATE = 44100
CHANNELS = 2
PCM_BITS = 24


@dataclass(frozen=True)
class PreparedAudio:
    path: Path
    sample_rate: int
    frame_count: int  # Frames per channel, not summed across channels.
    channels: int

    def validate(self, output_dir: Path) -> None:
        if not isinstance(self.path, Path) or not self.path.is_absolute():
            raise ValueError('Prepared audio path must be an absolute pathlib.Path')
        if not self.path.is_file() or self.path.suffix.lower() != '.wav':
            raise ValueError('Prepared audio must be an existing WAV file')
        if not self.path.resolve().is_relative_to(output_dir.resolve()):
            raise ValueError('Prepared audio must be inside its assigned output directory')
        if type(self.frame_count) is not int or self.frame_count <= 0:
            raise ValueError('Prepared audio must have a positive integer frame count')
        if self.sample_rate != SAMPLE_RATE or self.channels != CHANNELS:
            raise ValueError('Prepared audio must be 44100 Hz, stereo, 24-bit PCM WAV')
        # Encoding and full decode validation belong to the preparation implementation.
