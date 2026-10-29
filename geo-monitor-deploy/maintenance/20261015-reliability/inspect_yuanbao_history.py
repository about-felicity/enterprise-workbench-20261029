"""Read-only model reflection and original conversation history evidence."""
import json,sys,time
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-yuanbao')
from native_client import NativeClient
out=Path('/opt/monitor/geo-capture/maintenance/20261015-reliability/yuanbao-ack')
c=NativeClient(out)
try:
 c.connect()
 snapshots=c.script.exports_sync.snapshot('推荐一款祛痘精华液');(out/'all-matching-views.json').write_text(json.dumps(snapshots,ensure_ascii=False,indent=2));print(json.dumps({'views':[{'h':r['value'].get('h'),'question':r['value'].get('v')} for r in snapshots]},ensure_ascii=False))
 code=r'''
rpc.exports.inspect=function(cid){return new Promise((resolve,reject)=>Java.perform(()=>{try{
 const T=Java.use(MODEL_PREFIX+'T');
 function describe(o){return {type:String(o.getClass().getName()),methods:Array.from(o.getClass().getDeclaredMethods()).map(String),fields:Array.from(o.getClass().getDeclaredFields()).map(String)};}
 function unwrap(result){const fs=Array.from(result.getClass().getDeclaredFields()).filter(f=>String(f.getType().getName())==='java.lang.Object');if(fs.length!==1)throw Error('wrapper');fs[0].setAccessible(true);return Java.use('XP.e').getValue.call(Java.cast(fs[0].get(result),Java.use('XP.e')));}
 const messages=[];
 for(const id of [cid+'_1',cid+'_2',cid+'_3',cid+'_4',cid+'_local_id_0',cid+'_local_id_1']){try{messages.push({id:id,message:serializeModel(unwrap(T.i(cid,id)),0),entities:serializeModel(unwrap(T.d(0,cid,id)),0)});}catch(e){messages.push({id:id,error:String(e)});}}
 const classes={};for(const name of [MODEL_PREFIX+'ChatBizModel',MODEL_PREFIX+'ChatBizModel$GetConversationMessagesResult','com.tencent.hunyuan.mpcommon.generated.biz.chat.viewmodel.ChatListViewModel','com.tencent.hunyuan.mpcommon.generated.biz.chat.viewmodel.ChatPageScopeViewModel']){try{const C=Java.use(name);classes[name]={methods:Array.from(C.class.getDeclaredMethods()).map(String),fields:Array.from(C.class.getDeclaredFields()).map(String)};}catch(e){classes[name]={error:String(e)};}}
 resolve({T:{methods:Array.from(T.class.getDeclaredMethods()).map(String)},h:describe(T.h(cid)),g:describe(T.g(cid)),conversation:serializeModel(T.g(cid).a(),0),messages:messages,classes:classes});
}catch(e){resolve({error:String(e),stack:e.stack});}}));};
rpc.exports.lists=function(){return new Promise((resolve,reject)=>Java.perform(()=>{const rows=[];Java.choose('com.tencent.hunyuan.mpcommon.generated.biz.chat.viewmodel.ChatListViewModel',{onMatch:function(o){try{const v={};for(const f of Array.from(o.getClass().getDeclaredFields())){f.setAccessible(true);v[String(f.getName())]=serializeModel(Java.cast(f.get(o),Java.use('DQ.Q0')).getValue(),0);}rows.push(v);}catch(e){rows.push({error:String(e)});}},onComplete:function(){resolve(rows);}});}));};
rpc.exports.messages=function(){return new Promise((resolve,reject)=>Java.perform(()=>{const rows=[];Java.choose(MODEL_PREFIX+'Message',{onMatch:function(o){try{const v=serializeModel(o,0);if(String(v.serverId||'').startsWith('0RGfLig07CS_'))rows.push(v);}catch(e){}},onComplete:function(){resolve(rows);}});}));};
'''
 # Separate immutable reader script, no model hooks or mutating methods.
 bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
 schema=Path('/home/user/redroid-yuanbao/tools/chat_model_schema.json').read_text()
 script=c.session.create_script(bridge+'\nconst Java=bridge;\nconst MODEL_SCHEMA='+schema+';\n'+Path('/home/user/redroid-yuanbao/native_models.js').read_text()+code)
 script.load();data=script.exports_sync.inspect('0RGfLig07CS')
 messages=script.exports_sync.messages();(out/'heap-messages.json').write_text(json.dumps(messages,ensure_ascii=False,indent=2));print(json.dumps({'heap_messages':[{k:v for k,v in m.items() if k in ('id','serverId','serverIndex','pairId')} for m in messages]}))
 lists=script.exports_sync.lists();(out/'model-lists.json').write_text(json.dumps(lists,ensure_ascii=False,indent=2));print(json.dumps({'lists':lists},ensure_ascii=False))
 if 'error' in data:print(json.dumps(data));raise SystemExit(1)
 (out/'history-inspect.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 wcdb=c.session.create_script(bridge+'\nconst Java=bridge;\n'+Path('/tmp/yuanbao_wcdb_reader.js').read_text()+r'''
rpc.exports.history=function(cid){return withJava(function(){return stores.map(function(db,index){return {store:index,messages:query(db,"select * from yb_chat_message_table where conversationId='"+cid+"' order by msgIndex,repeatIndex,messageId"),conversation:query(db,"select * from yb_conversation_table where conversationId='"+cid+"'"),state:query(db,"select * from yb_message_state_table where conversationId='"+cid+"'")};});});};
''')
 wcdb.load();wcdb.exports_sync.discover();history=wcdb.exports_sync.history('0RGfLig07CS')
 (out/'wcdb-history.json').write_text(json.dumps(history,ensure_ascii=False,indent=2))
 print(json.dumps({'wcdb':[{'store':x['store'],'conversation_count':len(x['conversation']),'messages':[{k:v for k,v in m.items() if k not in ('rawContent','extInfo','extra','content','rawData')} for m in x['messages']]} for x in history]},ensure_ascii=False))
 # Entity contents stay in protected server evidence; print only identities.
 print(json.dumps({'at':time.time(),'classes':data['classes']},ensure_ascii=False))
finally:c.close()
