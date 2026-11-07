"""Run each external article read in a process with a hard wall-clock limit."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile


def fetch_article(url, *, timeout=90):
    with tempfile.TemporaryDirectory(prefix='creation-article-') as directory:
        result = Path(directory) / 'result.json'
        with subprocess.Popen(
            [sys.executable, '-B', '-m', 'creation.article_reader', url, str(result)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        ) as process:
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                return {'status': 'failed', 'text': '', 'error': f'Article read timed out after {timeout}s'}
        if code == 0 and result.is_file():
            return json.loads(result.read_text('utf-8'))
    return {'status': 'failed', 'text': '', 'error': f'Article reader exited ({code})'}


if __name__ == '__main__':
    from geo_source_cards.article_fetch import ScraplingArticleFetcher
    url, output = sys.argv[1:]
    Path(output).write_text(json.dumps(ScraplingArticleFetcher()(url), ensure_ascii=False), 'utf-8')
