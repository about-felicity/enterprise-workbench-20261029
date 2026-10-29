/* Read-only queries through this App's already-open WCDB handles. No keys. */
function withJava(work) {
    return new Promise(function (resolve, reject) {
        Java.perform(function () {
            try { resolve(work()); } catch (error) { reject(error); }
        });
    });
}
let stores = [];
function query(database, sql) {
    if (!/^select\s/i.test(sql) || sql.includes(';')) throw Error('Read-only SELECT required');
    const H = Java.use('com.tencent.wcdb.core.Handle');
    const S = Java.use('com.tencent.wcdb.core.PreparedStatement');
    const handle = database.g(false);
    let statement;
    try {
        statement = H.getOrCreatePreparedStatementWithSQL(handle.r(), sql);
        if (statement.toString() === '0') throw Error('Prepare failed');
        if (!S.checkPrepared(statement) && !S.prepareSQL(statement, sql)) throw Error('Prepare failed');
        if (!S.isReadOnly(statement)) throw Error('Non-read-only statement rejected');
        const count = S.getColumnCount(statement);
        const columns = [];
        for (let i = 0; i < count; i++) columns.push(String(S.getColumnName(statement, i)));
        const rows = [];
        while (true) {
            if (!S.step(statement)) throw Error('Read step failed');
            if (S.isDone(statement)) break;
            if (rows.length >= 1000) throw Error('Read limit exceeded');
            const row = {};
            for (let i = 0; i < count; i++) {
                const type = S.getColumnType(statement, i);
                const value = type === 5 ? null : S.getText(statement, i);
                row[columns[i]] = value === null ? null : String(value);
            }
            rows.push(row);
        }
        return rows;
    } finally {
        if (statement && statement.toString() !== '0') S.reset.overload('long').call(S, statement);
        handle.close();
    }
}
rpc.exports = {
    read: function (taskId) {
        if (!/^[a-f0-9-]{36}$/.test(taskId)) throw Error('Task UUID required');
        return withJava(function () {
            const result = [];
            stores.forEach(function (database, index) {
                const requests = query(database, "select * from yb_chat_message_table where instr(rawContent,'" + taskId + "')>0");
                const ids = Array.from(new Set(requests.map(r => r.conversationId)));
                ids.forEach(function (id) {
                    if (!id || !/^[A-Za-z0-9_-]{1,200}$/.test(id)) throw Error('Unexpected conversation identifier');
                    result.push({store:index,
                        messages:query(database, "select * from yb_chat_message_table where conversationId='" + id + "' order by msgIndex,repeatIndex,messageId"),
                        conversation:query(database, "select * from yb_conversation_table where conversationId='" + id + "'"),
                        state:query(database, "select * from yb_message_state_table where conversationId='" + id + "'")});
                });
            });
            return result;
        });
    },
    schema: function () {
        return withJava(function () {
            return stores.map(function (database, index) {
                return {store:index,schema:query(database, "select name,sql from sqlite_master where name in ('yb_chat_message_table','yb_conversation_table','yb_message_state_table','yb_session_table')")};
            });
        });
    },
    discover: function () {
        return new Promise(function (resolve, reject) {
            Java.perform(function () {
                const Database = Java.use('com.tencent.wcdb.core.Database');
                const Cpp = Java.use('com.tencent.wcdb.base.CppObject');
                const matches = [];
                Java.choose('com.tencent.wcdb.core.Database', {
                    onMatch:function (database) {
                        const ptr = Cpp.a(database);
                        const path = String(Database.getPath(ptr));
                        if (path.includes('/com.tencent.hunyuan.app.chat/files/.ybdb/') && Database.isOpened(ptr))
                            matches.push(Java.retain(database));
                    },
                    onComplete:function () {
                        setImmediate(function () {
                            Java.perform(function () {
                                try {
                                    stores.forEach(s => s.$dispose());
                                    stores = matches;
                                    resolve(stores.map(function (database, index) {
                                        return {store:index,tables:query(database, "select name from sqlite_master where type='table' order by name"),
                                            message_count:query(database, 'select count(*) as total from yb_chat_message_table'),
                                            recent_metadata:query(database, 'select speaker,status,msgIndex,length(rawContent) as bytes from yb_chat_message_table order by createTime desc limit 4')};
                                    }));
                                } catch (error) { reject(error); }
                            });
                        });
                    }
                });
            });
        });
    }
};
