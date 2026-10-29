Java.perform(function(){
 for(const name of ['com.larus.im.internal.legacy.NativeMessageServiceImpl','com.larus.im.internal.jni.service.OmniMessageService']) {
 const cls=Java.use(name);send({class:name,methods:cls.class.getDeclaredMethods().map(m=>m.toString()).filter(m=>/regenerat|sendMessage|reSend/i.test(m))});
 }
});
