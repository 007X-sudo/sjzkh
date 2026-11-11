# 视觉组学习工作台

面向零基础的视觉组入队考核学习辅助页面：16 个阶段、六项任务验收、41 道概念题、四个可视化演示、笔记与进度备份。

- 学习网站：https://007x-sudo.github.io/sjzkh/
- 手机扫码分享：https://007x-sudo.github.io/sjzkh/share.html

## 使用

使用手机或电脑浏览器打开网站，按学习阶段完成练习再自测；首页右上角可分享网址。微信内受限时切换至系统浏览器。

页面不编译 C++ / Python，也不代写考核作业；实际代码需在自己的开发环境运行。概念自测线是学习建议，不是官方分数线。

进度保存在浏览器本地，不上传到 GitHub。手机和电脑不自动同步；从本地 HTML 迁移到在线网站也需先导出 JSON，再导入。关闭或清理浏览器前请备份重要记录。

## GitHub Pages

发布分支为 `main`，目录为 `/ (root)`；`index.html` 是网站首页，`.nojekyll` 让页面按静态文件发布。原先上传的中文文件保留。

此仓库发布学习网页、学生管理演示及其 Python 示例源码，不含本地笔记、学生真实数据、JSON 备份或考核原 PDF。

## 学生信息管理系统

- 在线网站：https://007x-sudo.github.io/sjzkh/student-management/
- 支持增删改查、学号精确查询、四种成绩的双向排序。
- 页面适配手机；数据保存在当前浏览器，不上传、不跨设备同步。
- GitHub Pages 不执行 Python；Python 源码在 student-management/backend，下载包为 student-management/python-backend.zip。
- 本机运行与联调说明可从学生管理页面的“使用说明”获取。
