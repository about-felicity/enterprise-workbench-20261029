# 绩效显示模式切换

个人绩效明细新增“折线图 / 表格”切换按钮。默认折线图；表格模式直接恢复以前的完整每日列表，不再需要展开折叠表。两种模式共用已选日期及同一份数据，切换不会重算绩效或改变下方计算明细；更换员工时保留当前显示模式，页面重新加载后默认折线图。

仅修改PerformanceCenter.tsx与globals.css。生产构建及既有图表渲染检查通过。已发布主站和预览，公网版本和源码哈希验证见verification/release.json。未进行浏览器真实点击验收。原容器保留在对应名称加-before-view-toggle-20261031，原文件备份于服务器/opt/monitor/maintenance/performance-view-toggle-20261031/before。
