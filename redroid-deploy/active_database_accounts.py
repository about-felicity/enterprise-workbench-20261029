"""Compare currently open numeric IM databases, not historical messages."""
import subprocess, re, json
def current_uid(container):
    pid=subprocess.check_output(['docker','exec',container,'pidof','com.larus.nova'],text=True).strip()
    assert pid.isdigit(), 'Expected one main app process'
    links=subprocess.check_output(['docker','exec',container,'ls','-l','/proc/'+pid+'/fd'],text=True)
    ids=set(re.findall(r'/im_database_(\d+)(?:-wal|-shm)?(?:\s|$)',links))
    assert len(ids)==1, 'Cannot establish a unique current account from open databases'
    return ids.pop()
if __name__=='__main__':
    first=current_uid('doubao-hpe14-13-test')
    second=current_uid('doubao-hpe14-account2')
    print(json.dumps({'first_current_uid':'***'+first[-6:],'second_current_uid':'***'+second[-6:],'same_account':first==second}))
