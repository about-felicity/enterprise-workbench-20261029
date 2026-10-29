"""Launch an immutable panel-created native batch through the tested worker."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--config', type=Path, required=True)
args = parser.parse_args()
config = json.loads(args.config.read_text())
if config.get('backend')=='browser_extension':
    python='/opt/monitor/geo-capture/venv/bin/python'
    os.execv(python,[python,'-u','/opt/monitor/geo-capture/browser_task_bridge.py','--config',str(args.config)])

if config['model']=='deepseek2':
    python='/home/user/redroid-doubao/worker-venv/bin/python'
    os.execv(python,[python,'-u','/home/user/redroid-deepseek-account2/code/worker.py','--config',str(args.config)])
if config['model']=='deepseek':
    python='/home/user/redroid-doubao/worker-venv/bin/python'
    os.execv(python,[python,'-u','/home/user/redroid-deepseek/code/worker.py','--config',str(args.config)])
if config.get('prompt_mode')=='question_only' and config['model'] in {'doubao1','doubao2','yuanbao'}:
    python='/home/user/redroid-doubao/worker-venv/bin/python'
    os.execv(python,[python,'-u','/home/user/redroid-doubao/geo-batch-code/question_only_worker.py','--config',str(args.config)])
if config['model']=='yuanbao':
    python='/home/user/redroid-doubao/worker-venv/bin/python'
    command=[python,'-u','/home/user/redroid-yuanbao/worker.py','--config',str(args.config)]
    limit=int(os.environ.get('YUANBAO_CAPTURE_LIMIT','0'))
    if limit:command+=['--capture-limit',str(limit)]
    os.execv(python,command)
container, serial = {
    'doubao1': ('doubao-hpe14-13-test','127.0.0.1:5557'),
    'doubao2': ('doubao-hpe14-account2','127.0.0.1:5558'),
}[config['model']]
base = Path('/home/user/redroid-doubao')
python = str(base / 'worker-venv/bin/python')
subprocess.run([python,str(base/'runtime_preflight.py'),'--container',container],check=True)
questions = args.config.with_suffix('.questions.json')
if questions.exists():
    assert json.loads(questions.read_text()) == config['questions']
else:
    questions.write_text(json.dumps(config['questions'],ensure_ascii=False))
os.environ.update(DOUBAO_BATCH=config['batch'], DOUBAO_CONTAINER=container, DOUBAO_SERIAL=serial,
                  DOUBAO_QUESTIONS_FILE=str(questions), DOUBAO_ROUNDS=str(config['rounds']),
                  DOUBAO_SEND_INTERVAL=str(config['interval']), DOUBAO_ANSWER_TIMEOUT='900')
os.execv(python,[python,'-u',str(base/'geo-batch-code/geo_batch_bridge.py')])
