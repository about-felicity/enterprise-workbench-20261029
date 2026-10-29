import subprocess,re
c='doubao-hpe14-test';cmd=['docker','exec',c]
s=subprocess.check_output(cmd+['cat','/linkerconfig/ld.config.txt'],text=True)
s=re.sub(r'(namespace\.(?:default|system)\.permitted\.paths = [^\n]+\n)',r'\1namespace.\g<0>',s) if False else s
s=s.replace('namespace.default.permitted.paths = /system/${LIB}/drm','namespace.default.permitted.paths = /system/${LIB}/arm64:/system/${LIB}/arm:/system/${LIB}/drm')
s=s.replace('namespace.system.permitted.paths = /system/${LIB}/drm','namespace.system.permitted.paths = /system/${LIB}/arm64:/system/${LIB}/arm:/system/${LIB}/drm')
p=subprocess.run(['docker','exec','-i',c,'sh','-c','cat > /linkerconfig/ld.config.txt'],input=s,text=True,check=True)
subprocess.run(cmd+['setprop','ctl.restart','zygote'],check=True)
print('Test namespace permitted paths updated and test zygote restarted')
