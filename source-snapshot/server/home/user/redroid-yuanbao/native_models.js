/* Serialize App-owned immutable chat model snapshots; no network or writes. */
const MODEL_PREFIX = 'com.tencent.hunyuan.mpcommon.generated.biz.chat.bizmodel.';
function serializeModel(object, depth) {
    if (object === null || object === undefined) return null;
    if (depth > 18) throw Error('Model nesting limit exceeded');
    const name = String(object.getClass().getName());
    if (name === 'java.lang.String') return String(object.toString());
    if (name === 'java.lang.Boolean') return String(object.toString()) === 'true';
    if (['java.lang.Integer','java.lang.Short','java.lang.Byte','java.lang.Double','java.lang.Float'].includes(name)) return Number(String(object.toString()));
    if (name === 'java.lang.Long') return String(object.toString());
    const List = Java.use('java.util.List');
    if (List.class.isInstance(object)) {
        const list = Java.cast(object, List);
        const count = List.size.call(list);
        if (count > 5000) throw Error('Model collection limit exceeded');
        const values = [];
        for (let i=0; i<count; i++) values.push(serializeModel(List.get.call(list,i),depth+1));
        return values;
    }
    const schema = MODEL_SCHEMA[name];
    if (schema) {
        const cls = Java.use(name);
        const result = {_type:name.substring(MODEL_PREFIX.length)};
        const Lazy = Java.use('XP.e');
        Object.keys(schema).forEach(function (fieldName) {
            const field=cls.class.getDeclaredField(fieldName);field.setAccessible(true);
            const lazy=Java.cast(field.get(object),Lazy);
            result[schema[fieldName]]=serializeModel(Lazy.getValue.call(lazy),depth+1);
        });
        return result;
    }
    // Preserve enum and unsigned values without guessing completion semantics.
    return {_type:name,text:String(object.toString())};
}
rpc.exports = {
    conversationIds:function () {
        return new Promise(function(resolve,reject){Java.perform(function(){try {
            const ids=new Set(),Flow=Java.use('DQ.Q0'),Lazy=Java.use('XP.e');
            const name='com.tencent.hunyuan.mpcommon.generated.biz.chat.viewmodel.answer.entity.YbMarkdownViewModel';
            const field=Java.use(name).class.getDeclaredField('h');field.setAccessible(true);
            Java.choose(name,{
                onMatch:function(object){
                    const context=Java.cast(field.get(object),Flow).getValue();
                    if(context===null)return;
                    const cls=context.getClass(),schema=MODEL_SCHEMA[String(cls.getName())];
                    if(!schema)throw Error('Unsupported native context schema');
                    const key=Object.keys(schema).find(k=>schema[k]==='conversationId');
                    if(!key)throw Error('Native conversation identity field missing');
                    const cidField=cls.getDeclaredField(key);cidField.setAccessible(true);
                    const cid=Lazy.getValue.call(Java.cast(cidField.get(context),Lazy));
                    if(cid!==null && String(cid))ids.add(String(cid));
                },onComplete:function(){resolve(Array.from(ids).sort());}
            });
        }catch(error){reject(error);}});});
    },
    historyEntries:function () {
        return new Promise(function(resolve,reject){Java.perform(function(){try {
            // The legacy Android drawer can have the server title before the
            // DTMP history SQLite rows hydrate. Read only CID/title, no actions.
            const C=Java.use('com.tencent.hunyuan.deps.service.bean.chats.Session');
            const fields={};
            ['id','title'].forEach(function(name){
                fields[name]=C.class.getDeclaredField(name);fields[name].setAccessible(true);
            });
            const rows=[];
            Java.choose('com.tencent.hunyuan.deps.service.bean.chats.Session',{
                onMatch:function(object){
                    const cid=fields.id.get(object),title=fields.title.get(object);
                    if(cid!==null && title!==null && rows.length<5000)
                        rows.push({conversation_id:String(cid),title:String(title)});
                },onComplete:function(){resolve(rows);}
            });
        }catch(error){reject(error);}});});
    },
    readKnown:function (conversationId,messageId) {
        if (!/^[A-Za-z0-9_-]{1,160}$/.test(conversationId) || !/^[A-Za-z0-9_-]{1,160}$/.test(messageId)) throw Error('Invalid native identifier');
        return new Promise(function(resolve,reject){Java.perform(function(){
            try {
                const T=Java.use('com.tencent.hunyuan.mpcommon.generated.biz.chat.bizmodel.T');
                const last=T.h(conversationId).g();
                const info=T.g(conversationId).a();
                function unwrap(result) {
                    const fields=Array.from(result.getClass().getDeclaredFields()).filter(f=>String(f.getType().getName())==='java.lang.Object');
                    if(fields.length!==1)throw Error('Unsupported action result wrapper');
                    const field=fields[0];field.setAccessible(true);
                    const Lazy=Java.use('XP.e');
                    return Lazy.getValue.call(Java.cast(field.get(result),Lazy));
                }
                const lastValue=serializeModel(last,0);
                function readExact(id) {
                    const messageValue=serializeModel(unwrap(T.i(conversationId,id)),0);
                    if(messageValue.serverId!==messageId)throw Error('Exact native message identity unavailable');
                    resolve({last:lastValue,conversation:serializeModel(info,0),
                        content:serializeModel(unwrap(T.j(conversationId,id)),0),message:messageValue,
                        entities:serializeModel(unwrap(T.d(0,conversationId,id)),0),
                        question:serializeModel(unwrap(T.i(conversationId,messageValue.pairId)),0),
                        question_entities:serializeModel(unwrap(T.d(0,conversationId,messageValue.pairId)),0)});
                }
                if(lastValue.serverId===messageId) {readExact(lastValue.id);return;}
                // A local fetch-error placeholder can remain the last pointer
                // after the real response has arrived. Resolve the requested
                // server ID, never substitute the last answer or another turn.
                const name=MODEL_PREFIX+'Message',schema=MODEL_SCHEMA[name];
                const fieldName=Object.keys(schema).find(k=>schema[k]==='serverId');
                const idFieldName=Object.keys(schema).find(k=>schema[k]==='id');
                const cls=Java.use(name),Lazy=Java.use('XP.e');
                const serverField=cls.class.getDeclaredField(fieldName),idField=cls.class.getDeclaredField(idFieldName);
                serverField.setAccessible(true);idField.setAccessible(true);
                const ids=new Set();
                Java.choose(name,{
                    onMatch:function(object){
                        const server=String(Lazy.getValue.call(Java.cast(serverField.get(object),Lazy)));
                        if(server===messageId)ids.add(String(Lazy.getValue.call(Java.cast(idField.get(object),Lazy))));
                    },
                    onComplete:function(){try{
                        if(ids.size===0)throw Error('Exact native message is missing');
                        if(ids.size!==1)throw Error('Exact native message is ambiguous');
                        readExact(Array.from(ids)[0]);
                    }catch(error){reject(error);}}
                });
            } catch(error){reject(error);}
        });});
    },
    snapshot:function (wireQuestion) {
        return new Promise(function (resolve,reject) {
            Java.perform(function () {
                const names=['@markdown'];
                const references=[];
                function collect(index) {
                    if(index===names.length) {
                        setImmediate(function(){Java.perform(function(){
                            try { resolve(references.map(function(item){
                                if(item.kind==='@markdown') {
                                    const value={};
                                    const cls=item.object.getClass();const fields=cls.getDeclaredFields();
                                    for(let k=0;k<fields.length;k++) {
                                        if(String(fields[k].getType().getName())!=='DQ.Q0')continue;
                                        fields[k].setAccessible(true);
                                        const flow=Java.cast(fields[k].get(item.object),Java.use('DQ.Q0'));
                                        value[String(fields[k].getName())]=serializeModel(flow.getValue(),0);
                                    }
                                    return {kind:'markdown',value:value};
                                }
                                return {kind:item.kind,value:serializeModel(item.object,0)};
                            })); }
                            catch(error){reject(error);}
                            finally {references.forEach(item=>item.object.$dispose());}
                        });});
                        return;
                    }
                    const kind=names[index];
                    const className=kind==='@markdown'?'com.tencent.hunyuan.mpcommon.generated.biz.chat.viewmodel.answer.entity.YbMarkdownViewModel':MODEL_PREFIX+kind;
                    Java.choose(className,{
                        onMatch:function(object){
                            if(wireQuestion) {
                                const field=object.getClass().getDeclaredField('v');field.setAccessible(true);
                                const flow=Java.cast(field.get(object),Java.use('DQ.Q0'));
                                if(String(flow.getValue())!==wireQuestion)return;
                            }
                            references.push({kind:kind,object:Java.retain(object)});
                        },
                        onComplete:function(){collect(index+1);}
                    });
                }
                collect(0);
            });
        });
    }
};
