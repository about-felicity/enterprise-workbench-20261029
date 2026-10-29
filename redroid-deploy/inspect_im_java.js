Java.perform(function () {
  const names = [
    'com.larus.im.internal.core.conversation.ConversationLocalManager',
    'com.larus.im.internal.jni.service.OmniConversationService',
    'com.larus.im.internal.jni.callback.NativeIMCallback',
    'com.larus.im.internal.jni.callback.OmniIMCallback',
    'com.larus.im.internal.jni.NativeOmniSDKInitializer',
    'com.larus.im.internal.jni.OmniCppHelper',
    'com.larus.im.internal.jni.OmniIMSDK',
    'com.larus.im.internal.core.conversation.ConversationServiceImpl'
  ];
  for (const name of names) {
    try {
      const cls=Java.use(name);
      send({class:name, fields:cls.class.getDeclaredFields().map(f=>f.getName().toString()),
        methods:cls.class.getDeclaredMethods().map(m=>m.getName().toString()+':'+m.getParameterTypes().map(t=>t.getName().toString()).join(',')).filter(m=>!m.includes('lambda')).slice(0,80)});
    } catch(e) { send({class:name,error:e.toString()}); }
  }
  const lm=Java.use(names[0]);
  if (lm.INSTANCE.value) send({conversation_version:lm.INSTANCE.value.getConversationVersion().toString()});
  Java.choose('com.larus.im.internal.jni.NativeConversationDaoImpl',{onMatch:function(o){send({dao_native_count:o.getAllConversationCount().toString()})},onComplete:function(){send({dao_inspection_done:true})}});
  for(const name of ['com.larus.im.callback.IIMCallback','com.larus.im.internal.jni.bean.OmniIMError','com.larus.im.internal.core.conversation.ConversationServiceImpl$Companion']) {
    const cls=Java.use(name);
    send({class:name,methods:cls.class.getDeclaredMethods().map(m=>m.toString())});
  }
  Java.choose('com.larus.im.internal.jni.OmniIMSDK',{onMatch:function(o){send({sdk_uid_tail:o.uid.value.slice(-6),released:o.released.value,helper_path_tail:o.getHelper().getPath().slice(-6)})},onComplete:function(){send({sdk_inspection_done:true})}});
});
