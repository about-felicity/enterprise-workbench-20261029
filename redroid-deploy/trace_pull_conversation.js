Java.perform(function () {
  const cbcls=Java.use('com.larus.im.internal.jni.callback.NativeIMCallback');
  cbcls.onFailure.implementation=function(error){
    send({native_failure:true,code:error.component1(),error_fields:error.getClass().getDeclaredFields().map(f=>f.getName().toString())});
    return this.onFailure(error);
  };
  cbcls.onSuccess.implementation=function(result){
    const type=result ? result.getClass().getName().toString() : null;
    send({native_success_type:type});
    if(type==='com.larus.im.internal.jni.bean.OmniGetConversationResponse') {
      const obj=Java.cast(result,Java.use(type));
      const fields=obj.getClass().getDeclaredFields();
      send({response_fields:fields.map(f=>f.getName().toString()+':'+f.getType().getName().toString())});
      for(const f of fields){
        const name=f.getName().toString();
        if (name.toLowerCase().includes('conversation')){
          f.setAccessible(true); const v=f.get(obj);
          send({field:name,is_null:v===null,type:v ? v.getClass().getName().toString() : null,
            child_fields:v ? v.getClass().getDeclaredFields().map(x=>x.getName().toString()+':'+x.getType().getName().toString()) : []});
        }
      }
    }
    return this.onSuccess(result);
  };
  const Callback=Java.registerClass({name:'com.larus.diagnostic.MetadataCallback',implements:[Java.use('com.larus.im.callback.IIMCallback')],methods:{
    mustInMain:function(){return false},
    onFailure:function(error){send({metadata_failure_class:error.getClass().getName().toString(),methods:error.getClass().getDeclaredMethods().map(m=>m.getName().toString())})},
    onSuccess:function(result){send({metadata_success_type:result ? result.getClass().getName().toString() : null,fields:result ? result.getClass().getDeclaredFields().map(f=>f.getName().toString()+':'+f.getType().getName().toString()) : []})}
  }});
  const cls=Java.use('com.larus.im.internal.core.conversation.ConversationServiceImpl');
  const service=cls.Companion.value.get();
  send({service_class:service.getClass().getName().toString()});
  service.getAndSyncRemoteConversation('38436542168665602','recovery_metadata_probe',Callback.$new(),Java.use('java.util.HashMap').$new());
  Java.choose('com.larus.im.internal.jni.OmniIMSDK',{onMatch:function(o){send({sdk_uid_tail:o.uid.value.toString().slice(-6),released:o.released.value})},onComplete:function(){}});
  Java.enumerateLoadedClasses({onMatch:function(name){if(name.includes('omni')||name.includes('Omni')||name.includes('WCDB')){if(/Log|Error/.test(name))send({log_class:name})}},onComplete:function(){}});
});
