from remote import connect
import shlex
c,p=connect(); cmd='docker exec doubao-hpe14-13-test logcat -b all -d | grep -E "houdini|Fatal signal|native_method|is not accessible|CANNOT LINK|FATAL EXCEPTION" | tail -30'
i,o,e=c.exec_command('sudo -S -p "" bash -lc '+shlex.quote(cmd));i.write(p+'\n');i.flush();i.channel.shutdown_write();print(o.read().decode('utf8','replace'));c.close()
