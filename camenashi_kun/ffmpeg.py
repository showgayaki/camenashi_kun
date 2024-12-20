import subprocess
from pathlib import Path
from logging import getLogger


logger = getLogger(__name__)


class Ffmpeg:
    def __init__(self, crf) -> None:
        self.mega = 10**6
        self.crf = crf

    def compress(self, video_file_path: Path) -> Path:
        compressed_file_path = Path(video_file_path.parent).joinpath(f'{video_file_path.stem}_comporessed{video_file_path.suffix}')
        try:
            # ffmpeg -i {video_file_path} -crf 18 {compressed_file_path}
            subprocess.run(['ffmpeg', '-i', str(video_file_path), '-crf', self.crf, str(compressed_file_path)])

            # 圧縮前後のファイルサイズ
            size_before = video_file_path.stat().st_size / self.mega
            size_after = compressed_file_path.stat().st_size / self.mega
            logger.info(f'Compression succeeded. Before: {size_before:.1f} MB, After: {size_after:.1f} MB')

            # 圧縮に成功したら、元のファイルは削除する
            logger.info(f'Deleting the file: {video_file_path}')
            Path(video_file_path).unlink()

            return compressed_file_path
        except Exception as e:
            logger.error(f'Compression failed: {e}')
            return video_file_path
