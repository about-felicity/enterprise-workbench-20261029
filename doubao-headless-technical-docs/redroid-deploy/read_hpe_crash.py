from remote import connect
import shlex
c,p=connect(); cmd='docker exec doubao-hpe14-test logcat -d | grep -E "FATAL EXCEPTION|Fatal signal|houdini|UnsatisfiedLinkError|dlopen failed|cannot locate|Process.*nova|Abort message|SIGSEGV|SIGABRT" | tail -70'
i,o,e=c.exec_command('sudo -S -p "" bash -lc '+shlex.quote(cmd));i.write(p+'\n');i.flush();i.channel.shutdown_write();print(o.read().decode('utf8','replace'));c.close()
