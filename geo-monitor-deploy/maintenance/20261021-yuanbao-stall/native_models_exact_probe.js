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
                const id=messageId;
                const content=unwrap(T.j(conversationId,id));
                const message=unwrap(T.i(conversationId,id));
                const entities=unwrap(T.d(0,conversationId,id));
                const question=unwrap(T.i(conversationId,lastValue.pairId));
                const questionEntities=unwrap(T.d(0,conversationId,lastValue.pairId));
                resolve({last:lastValue,conversation:serializeModel(info,0),content:serializeModel(content,0),message:serializeModel(message,0),entities:serializeModel(entities,0),question:serializeModel(question,0),question_entities:serializeModel(questionEntities,0)});
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
