# 无头模拟器测试结果（2026-10-06）

三题均由服务器上的 Android 15 Redroid 内豆包 App 发出并收到完整回答，测试时已关闭 scrcpy 投屏。
直接读取模拟器中的聊天 SQLite 数据库（只读事务），提取原始 Markdown 正文、37 条信源记录和 15 处引用信息。重复信源保留原始编号。

连续稳定运行未通过：App 后续出现 ARM 转译组件错误 `guest_params_arch.h:278: CHECK failed: 32080 <= 0`，并发生 SIGABRT。UI 也曾停在搜索状态，尽管答案已经写入数据库。
这份结果证明数据可提取，不代表当前 x86 转译环境可以长期无人值守。测试没有停止或重启原有业务容器。

## 字段说明

`sources` 是搜索参考资料列表；`citations` 是正文实际引用，包含原始位置、标题、URL、doc_id。两者分别保存。
正文中的时间、地址等内容是豆包原始输出，未在本测试中独立核验。

## 第 1 题

请联网检索：中国国家博物馆的官方地址和开放时间是什么？请简洁回答，并提供官方信源链接。

**官方地址**：北京市东城区东长安街16号（天安门广场东侧）
**开放时间**：9:00‑17:30（16:30停止入馆）；每周一闭馆，法定节假日除外；6‑10月执行该夏令时间，其余年份常规：9:00‑17:00（16:00停止入馆）
**官方信源**：https://www.chnmuseum.cn/cg/

>提示：实行实名预约参观，免费入馆。

参考资料：12 条；正文引用：4 处。

- 1. [服务_中国国家博物馆官方网站](https://www.chnmuseum.cn/cg/?eqid=a3920ff90000629800000003647448c2)
- 2. [中国国家博物馆官方网站](https://www.chnmuseum.cn/?from=www.13dh.com)
- 3. [参观导览 - 启蒙的艺术 - 中国国家博物馆](https://www.chnmuseum.cn/Portals/0/web/zt/qimeng/cn/visit.html)
- 4. [服务_中国国家博物馆官方网站](https://www.chnmuseum.cn/cg/?eqid=c6d7fda500032b200000000664454925)
- 5. [中国国家博物馆](https://pcticket.chnmuseum.cn/commentate/general)
- 6. [温馨提示_中国国家博物馆官方网站](https://www.chnmuseum.cn/gbgg/202609/t20260918_282606.shtml)
- 7. [中国国家博物馆官方网站](http://www.chnmuseum.cn/)
- 8. [中国国家博物馆参观门票领取办法及开放时间](https://m.chnmuseum.cn/Portals/0/web/exhibition/zx/201703.pdf)
- 9. [资讯](https://www.chnmuseum.cn/zx/)
- 10. [中国国家博物馆官方网站](https://www.chnmuseum.cn/?from=owdir.com)
- 11. [中国国家博物馆文章](http://chnmuseum.cn/?ref=www.bidianer.com)
- 12. [视频_中国国家博物馆官方网站](https://www.chnmuseum.cn/sp/)

## 第 2 题

请联网检索：故宫博物院的官方购票预约入口是什么？用三句话回答并附官方信源。

故宫博物院主要官方购票预约入口为微信端的“故宫博物院”小程序，同时官网设有在线订票页面ticket.dpm.org.cn跳转该预约渠道。
该院并未授权任何第三方机构、个人代办门票预约，全部观众都需要实名在此官方渠道完成购票预约。
门票会在参观日前7天的20点开放预约，景区不售卖当日现场门票。
官方信源：故宫博物院官网在线订票页面 http://ticket.dpm.org.cn/

参考资料：9 条；正文引用：4 处。

- 1. [在线订票 - 故宫博物院](http://ticket.dpm.org.cn/)
- 2. [故宫博物院](https://www.dpm.org.cn/Home.html#!/xh)
- 3. [关于2026年故宫博物院年票发售的公告 - 故宫博物院](https://www.dpm.org.cn/announce_detail/372863.html)
- 4. [故宫博物院参观须知 - 故宫博物院](https://www.dpm.org.cn/singles_detail/259831.html)
- 5. [故宫博物院](https://www.dpm.org.cn/home.htm/)
- 6. [导览 - 故宫博物院](https://www.dpm.org.cn/Visit.html?ivk_sa=1024320u)
- 7. [在线订票 - 故宫博物院](https://www.dpm.org.cn/subject_booking/)
- 8. [故宫博物院](https://www.dpm.org.cn/Home.html#!/h)
- 9. [故宫博物院关于2026年7月27日开放的公告 - 故宫博物院](https://www.dpm.org.cn/announce_detail/379398.html)

## 第 3 题

请联网检索：Python 官方文档中列表和元组有什么区别？请用三点简洁说明，并附官方文档信源链接。

### Python官方文档：列表(list)与元组(tuple)三点区别
1. **可变性不同**：列表是**可变(mutable)**序列，可以修改、增删内部元素；元组是**不可变(immutable)**序列，不支持对单个元素赋值修改。
2. **典型存储元素类型不同**：列表通常存放**同质（同类型）**元素；元组通常存放**异质（不同类型）**元素，常配合解包使用。
3. **语法字面量不同**：列表使用方括号`[]`构建；元组使用圆括号`()`（括号可省略，单元素元组必须带尾随逗号）构建。

> 官方中文信源链接：
> https://docs.python.org/zh-cn/3.13/tutorial/datastructures.html

> 官方内置类型参考链接：
> https://docs.python.org/zh-cn/3.13/library/stdtypes.html

引用原文片段：
> 元组是 immutable（不可变的），一般可包含异质元素序列，通过解包或索引访问。列表是 mutable（可变的），列表元素一般为同质类型，可迭代访问。

参考资料：16 条；正文引用：7 处。

- 1. [5. 数据结构 — Python 3.13.15 文档](https://docs.python.org/zh-cn/3.13/tutorial/datastructures.html)
- 2. [5. Data Structures](https://docs.python.org/3/tutorial/datastructures.html?highlight=tuple)
- 3. [5. Struktur Data](https://docs.python.org/id/3.11/tutorial/datastructures.html)
- 4. [5. Struktur Data](https://docs.python.org/id/3.5/tutorial/datastructures.html)
- 5. [内置类型 — Python 3.13.15 文档](https://docs.python.org/zh-cn/3.13/library/stdtypes.html)
- 6. [Built-in Types](https://docs.python.org/3.12/library/stdtypes.html?highlight=__dict__)
- 7. [5. 数据结构 — Python 3.14.7 文档](https://docs.python.org/zh-cn/3/tutorial/datastructures.html?highlight=%E5%88%97%E8%A1%A8)
- 8. [5. Data Structures](https://docs.python.org/3/tutorial/datastructures.html?highlight=list+comprehension)
- 9. [5. Estruturas de dados](https://docs.python.org/pt-br/3.10/tutorial/datastructures.html)
- 10. [5. Structures de données](https://docs.python.org/fr/3.13/tutorial/datastructures.html)
- 11. [5. データ構造](https://docs.python.org/ja/3/tutorial/datastructures.html?highlight=remove)
- 12. [5. Struktury danych](https://docs.python.org/pl/3.11/tutorial/datastructures.html)
- 13. [Built-in Types](https://docs.python.org/3/library/stdtypes.html?highlight=truth)
- 14. [内置类型 — Python 3.11.15 文档](https://docs.python.org/zh-cn/3.11/library/stdtypes.html)
- 15. [5. Data Structures](https://docs.python.org/3.16/tutorial/datastructures.html)
- 16. [5. 资料结构 — Python 3.13.15 说明文件](https://docs.python.org/zh-tw/3.13/tutorial/datastructures.html)
