# 公网加载延迟排查与恢复（2026-10-29）

访问入口：https://1any.top/geo_monitor/

## 确认原因

本地首页约0.07秒、内容上传状态接口约0.11秒；公网未登录入口正常返回302。但是公网服务器经127.0.0.1:13000访问本地首页及状态接口，35秒内没有收到任何响应，Nginx记录多个业务接口upstream timed out。

本地monitor-vps2-tunnel服务持续失败，累计重启超过3200次，错误为remote port forwarding failed for listen port 13000。公网sshd会话PID40906同时占用13000和18765，积压大量CLOSE-WAIT连接；其请求无法到达正常运行的本地应用。服务端ClientAliveInterval=0，失效会话未及时释放转发端口，新的隧道无法绑定。

## 修复

确认PID40906只监听工作台两个转发端口且为sshd root会话后，仅终止该失效会话；重启本地monitor-vps2-tunnel，恢复转发。未重启写作、采集、dashboard、Nginx或sshd主服务。

备份/etc/ssh/sshd_config，在Match User root作用域添加ClientAliveInterval 30与ClientAliveCountMax 3。通过sshd -t及sshd -T -C有效配置检查后reload sshd，今后的root隧道连接具备服务端失联检测。备份：/root/geo-monitor-access-backups/public-latency-20261029/sshd_config。没有改变认证规则、授权密钥或GatewayPorts。

## 复测

隧道新进程18161保持active/running，NRestarts固定3219，没有继续增长。

使用短时受控认证会话，未输出会话密钥、未更改用户登录信息：

| 测试路径 | 公网服务器侧总耗时 | 本地网络经公网总耗时 |
| --- | ---: | ---: |
| 登录后首页 | 1.09秒 | 4.696秒 |
| 控制状态API | 1.09秒 | 1.468秒 |
| 内容上传状态API | 1.087秒 | 7.667秒 |

所测页面、CSS、JS和接口均HTTP200。这里是分请求HTTP测量，不等同于完整浏览器页面渲染时间。公网网络仍有波动；其中一轮出现DNS解析超时，后续恢复。不能将当前修复表述为公网延迟归零，也不能由本次结果推断所有历史大图慢传均已解决。

主要故障“页面请求一直挂起至超时”已恢复。剩余跨网传输仍比内网慢。机器结果见同目录verification。
