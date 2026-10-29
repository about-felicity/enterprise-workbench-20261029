Java.perform(function(){
 Java.enumerateLoadedClasses({onMatch:function(name){
   if(/^com\.tencent\.wcdb/.test(name) && !name.includes('$')) {
     const cls=Java.use(name);
     send({class:name,methods:cls.class.getDeclaredMethods().map(m=>m.getName().toString()+':'+m.getParameterTypes().map(t=>t.getName().toString()).join(',')).filter(n=>/trace|error|message|token|register|sqlite/i.test(n)).slice(0,50)});
   }
 },onComplete:function(){}});
});
