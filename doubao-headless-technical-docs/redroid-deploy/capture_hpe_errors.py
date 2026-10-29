from remote import connect
import shlex,pathlib
c,p=connect();cmd='docker exec doubao-hpe14-13-test logcat -b all -d | grep -E "ANR in com.larus.nova|F berberis|FATAL EXCEPTION|Fatal signal|Abort message" | tail -40'
i,o,e=c.exec_command('sudo -S -p "" bash -lc '+shlex.quote(cmd));i.write(p+'\n');i.flush();i.channel.shutdown_write();s=o.read().decode('utf8','replace');pathlib.Path('redroid-deploy/test-results/hpe14-native-errors.log').write_text(s,encoding='utf8');print(s or 'No native fatal / ANR records after test emulator restart');c.close()
