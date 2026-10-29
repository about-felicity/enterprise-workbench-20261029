# 产品图片上传入口（2026-10-24）

已上线：知识库 Word 上传旁新增产品图片上传。共享当前选中的产品，支持已入库产品及待分析知识库；待分析知识库发布后仍能关联其图片。新增产品先上传知识库，再上传产品图片。

支持静态 JPG、PNG、WebP，每张 5MB 内、2500 万像素内，可逐张上传多张。保存原始字节，记录文件名、尺寸、大小、SHA256 和上传时间。上传前可本地预览，上传中显示状态、禁用重复操作，产品卡片显示缩略图和原图链接。手机布局上下排列。

后端 20 项回归测试及 33 项网关测试通过，生产构建成功。实际主界面上传临时图片，核对原图字节、刷新后的持久显示及手机布局，浏览器错误为零。测试图片已清理。采集及创作进程 PID 与启动时间保持不变。

服务器依赖增加 Pillow 12.3.0（`/home/user/geo-editorial/venv`）；重建环境时安装 `geo-monitor-deploy/creation/requirements-images.txt`。图片存储在 `/opt/monitor/geo-content/studio/images/image-*/`，包含 `original` 和 `metadata.json`。

备份：`/opt/monitor/geo-content/maintenance/product-images-20261024/before`；旧镜像：`monitor-dashboard:before-product-images-20261024`。验收、构建与发布记录见本目录 `verification`。
