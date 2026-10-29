# 2026-10-17 采集面板连接提示恢复修复

用户截图提示连接中断。实际检查：dashboard-api自02:36:30 UTC未重启，自动RestartCount=0，约1.506GiB/8GiB；8803/api/panel HTTP200耗时0.086秒。DeepSeek已4/63，文心115/168，两个采集服务在继续。

代码refresh()确有缺陷：catch向共用notice写入连接中断，后续成功虽connected=true且恢复按钮，却从不移除此提示。因此过去一次读取失败会遗留红条；无法据此证明截图瞬间究竟是网络超时、HTTP失败或渲染异常，历史无浏览器错误明细，不虚构具体断网原因。

仅修panel.html：连接警告使用独立connectionNotice，成功轮询自动清空；其他操作提示不受影响。失败时仍立即禁用写操作并保留旧进度，5秒自动刷新/15秒超时不变。文案说明面板状态读取失败不等于后台采集停止。

真实Chrome只读回归模拟HTTP503→5秒自动恢复、网络失败→恢复、畸形JSON→恢复，检查警告可见/消失、connected门禁和原操作提示保留；6次隔离状态请求、JS错误0、生产POST0。正式公网https://1any.top/geo_monitor/#capture/deepseek真实iframe读到新connectionNotice，6模型加载且警告隐藏，JS错误0、非GET0。

直接替换动态读取HTML，无服务或采集重启。备份服务器同目录panel-before.html。79/79源码映射一致。用户已有页面需要刷新一次加载新HTML。
