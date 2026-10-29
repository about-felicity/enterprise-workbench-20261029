"""Ordinary Python bootstrap; no generated or executed PowerShell script files."""
import argparse,hashlib,json,os,socket,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path

def verify(package):
    manifest=json.loads((package/'manifest.json').read_text(encoding='utf-8'))
    for name,digest in manifest.items():
        p=(package/name).resolve()
        if not p.is_relative_to(package.resolve()) or not p.is_file():raise RuntimeError('Package file missing: '+name+'; extract the complete ZIP again.')
        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise RuntimeError('Package file changed: '+name+'; use the complete original ZIP.')

def health():
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with op.open('http://127.0.0.1:8767/api/health',timeout=2) as r:return json.load(r)
    except Exception:return None

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    package=Path(__file__).resolve().parent.parent
    root=Path(os.environ['LOCALAPPDATA'])/'DeepSeekCollector'/'App'
    stage='Package integrity';log=None
    try:
        print('[1/4] Checking complete package...',flush=True);verify(package)
        stage='Writable application directory';root.mkdir(parents=True,exist_ok=True)
        log=root.parent/'startup-error.txt'
        with tempfile.NamedTemporaryFile(dir=root,prefix='write-check-'):pass
        stage='Existing receiver check';current=health()
        expected=(root/'data/deepseek_results.jsonl').resolve()
        if current:
            if not current.get('ok') or Path(current.get('results_path','')).resolve()!=expected:raise RuntimeError('Port 8767 belongs to a different receiver. No process was stopped. Close the previous collector before switching packages.')
            print('Receiver already running; no duplicate process started.',flush=True)
            print('Chrome extension folder: '+str(package/'extension'),flush=True);return 0
        with socket.socket() as probe:
            try:probe.bind(('127.0.0.1',8767))
            except OSError as e:raise RuntimeError('Port 8767 is occupied. No process was stopped; inspect the existing application.') from e
        stage='Runtime files preparation'
        for name in ['enrollment.py','local_receiver.py','remote_sync.py']:
            data=(package/'app'/name).read_bytes();target=root/name
            if not target.exists() or target.read_bytes()!=data:target.write_bytes(data)
        (root/'config').mkdir(exist_ok=True)
        target=root/'config/public_upload.json';data=(package/'config/public_upload.json').read_bytes()
        if not target.exists() or target.read_bytes()!=data:target.write_bytes(data)
        if args.check:
            print('Package, writable directory and receiver port checks passed. No registration or collection started.',flush=True);return 0
        stage='Device registration';print('[3/4] Preparing upload device...',flush=True)
        sys.path.insert(0,str(root));from enrollment import prepare
        config=prepare(root)
        print('Upload credentials ready.' if config.get('token') else 'Offline: results will stay local; registration retries automatically.',flush=True)
        stage='Receiver launch';print('[4/4] Starting local receiver...',flush=True)
        data_dir=root/'data';data_dir.mkdir(exist_ok=True)
        env={**os.environ,'DEEPSEEK_MONITOR_DATA_DIR':str(data_dir),'DEEPSEEK_REMOTE_SYNC_CONFIG':str(root/'config/deepseek_sync.json'),'DEEPSEEK_REMOTE_DEVICE':'deepseek-browser-extension'}
        with (data_dir/'receiver.log').open('ab') as out,(data_dir/'receiver_error.log').open('ab') as err:
            process=subprocess.Popen([sys.executable,'-X','utf8','-B',str(root/'local_receiver.py')],cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,close_fds=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        for _ in range(30):
            current=health()
            if current and current.get('ok') and Path(current.get('results_path','')).resolve()==expected:
                print('READY: receiver http://127.0.0.1:8767',flush=True)
                print('Chrome extension folder: '+str(package/'extension'),flush=True)
                print('Load that folder in chrome://extensions, then log in to DeepSeek and click Start in the extension.',flush=True);return 0
            if process.poll() is not None:raise RuntimeError('Receiver exited. See '+str(data_dir/'receiver_error.log'))
            time.sleep(.4)
        raise RuntimeError('Receiver did not become ready. See '+str(data_dir/'receiver_error.log'))
    except Exception as e:
        message=f'Stage: {stage}\nError: {type(e).__name__}: {e}\nPath: {getattr(e,"filename",None) or root}\n'
        print(message,file=sys.stderr,flush=True)
        candidates=[log,Path(tempfile.gettempdir())/'DeepSeekCollector-startup-error.txt']
        for candidate in candidates:
            if candidate:
                try:candidate.write_text(message,encoding='utf-8');print('Diagnostic log: '+str(candidate),file=sys.stderr);break
                except OSError:pass
        return 1

if __name__=='__main__':raise SystemExit(main())
