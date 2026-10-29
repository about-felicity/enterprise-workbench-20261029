# 抓取逻辑参考

`wenxin-baidu-collector/`是用户指定仓库的独立只读参考副本，不是新的生产采集任务，不与当前浏览器profile或队列共用数据。

- 上游：[about-felicity/wenxin-baidu-collector](https://github.com/about-felicity/wenxin-baidu-collector)。
- 本次固定commit：`8789ea281b201b6ec7a9770ddb24f6ac5f800929`。
- 当前生产采集源码仍在`../geo-source-card-collectors/`及服务器独立GEO venv；不从参考目录直接运行supervisor。
- 核对记录：[REFERENCE_REVIEW.md](REFERENCE_REVIEW.md)。
