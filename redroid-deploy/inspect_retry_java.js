Java.perform(function(){
 Java.choose('com.larus.im.internal.jni.OmniIMSDK',{onMatch:function(o){
   if(o.uid.value.toString().endsWith('066524')){
     const s=o.getMessageService();
     send({class:s.getClass().getName().toString(),methods:s.getClass().getDeclaredMethods().map(m=>m.toString()).filter(m=>/resend|retry/i.test(m))});
   }
 },onComplete:function(){}});
 const s=Java.use('com.larus.im.internal.legacy.NativeMessageServiceImpl');
 send({methods:s.class.getDeclaredMethods().map(m=>m.toString()).filter(m=>/resend|retry/i.test(m))});
});
