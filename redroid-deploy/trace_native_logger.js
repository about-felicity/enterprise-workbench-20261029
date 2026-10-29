Java.perform(function(){
 const name='com.larus.im.internal.jni.dependency.OmniLoggerCallByNative';
 const cls=Java.use(name);
 send({logger_methods:cls.class.getDeclaredMethods().map(m=>m.getName().toString()+':'+m.getParameterTypes().map(t=>t.getName().toString()).join(','))});
 for (const n of new Set(cls.class.getDeclaredMethods().map(m=>m.getName().toString()))) {
   if(n!=='printLog' || !cls[n] || !cls[n].overloads)continue;
   for(const ov of cls[n].overloads){
     if(!ov.argumentTypes.some(t=>t.className==='java.lang.String'))continue;
     ov.implementation=function(...args){
       const strings=args.filter((v,i)=>ov.argumentTypes[i].className==='java.lang.String').map(v=>v===null?'':v.toString());
       const all=strings.join(' ');
       if(/conversation|wcdb|sqlite|database/i.test(all) && /error|fail|SQL|insert|invalid/i.test(all)){
         const clean=all.replace(/MS4[^\s:]+/g,'[account]').replace(/https?:\/\/[^\s]+/g,'[url]').replace(/"(?:\\.|[^"\\])*"|'[^']*'/g,'[value]').replace(/\d{8,}/g,'[id]');
         if(!/token|cookie|authorization|password|secret/i.test(clean))send({native_log:clean.slice(0,2000)});
       }
       return ov.call(this,...args);
     };
   }
 }
 const cbcls=Java.use('com.larus.im.internal.jni.callback.NativeIMCallback');
 cbcls.onSuccess.implementation=function(result){
   if(result && result.getClass().getName().toString()==='com.larus.im.internal.jni.bean.OmniGetConversationResponse'){
     const obj=Java.cast(result,Java.use('com.larus.im.internal.jni.bean.OmniGetConversationResponse'));
     const conv=Java.cast(obj.conversation.value,Java.use('com.larus.im.internal.jni.bean.OmniConversation'));
     send({response_conversation_id:conv.conversationId.value.toString(),version:conv.version.value.toString(),deleted:conv.isDeleted.value,local:conv.isLocal.value,create_time:conv.createTime.value.toString(),type:conv.conversationType.value.toString(),status:conv.status.value.toString()});
   }
   return this.onSuccess(result);
 };
 const service=Java.use('com.larus.im.internal.core.conversation.ConversationServiceImpl').Companion.value.get();
 service.pullRemoteConversation('38436542168665602','recovery_metadata_probe',Java.use('java.util.HashMap').$new());
});
