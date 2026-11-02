from pathlib import Path
import sys,runpy
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'maintenance/task-load-20261029/ssh-deps'))
runpy.run_path(str(Path(__file__).with_name('tunnel.py')),run_name='__main__')
