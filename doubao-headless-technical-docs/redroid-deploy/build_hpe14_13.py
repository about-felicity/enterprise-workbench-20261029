import subprocess,pathlib,json
r=pathlib.Path('/home/user/redroid-doubao'); w=r/'hpe14-build'
(w/'Dockerfile13').write_text('FROM erstt/redroid:13.0.0_houdini_ChromeOS\nCOPY system/ /system/\n')
subprocess.run(['docker','stop','doubao-hpe14-test'],check=True)
subprocess.run(['docker','build','--network=none','-f',str(w/'Dockerfile13'),'-t','doubao/redroid:13-hpe14-com1.3',str(w)],check=True)
subprocess.run(['docker','volume','create','doubao-hpe14-android13-data'],check=True)
subprocess.run(['docker','run','-d','--name','doubao-hpe14-13-test','--privileged','--cpus','2','--memory','3g','-p','127.0.0.1:5557:5555','-v','doubao-hpe14-android13-data:/data','doubao/redroid:13-hpe14-com1.3','ro.enable.native.bridge.exec64=1','ro.dalvik.vm.native.bridge=libhoudini.so','androidboot.use_memfd=1','androidboot.redroid_gpu_mode=guest','androidboot.redroid_width=720','androidboot.redroid_height=1280','androidboot.redroid_dpi=320','androidboot.redroid_net_ndns=2','androidboot.redroid_net_dns1=223.5.5.5','androidboot.redroid_net_dns2=119.29.29.29'],check=True)
