# Linux DO Post Auditor

一个用于预审 LINUX DO 发帖草稿的 Codex Skill。

它帮助检查：

- 全局版规风险
- 分区是否匹配
- 标签是否完整
- 网盘、推广、交易、求职、求助等特殊帖子的必填信息
- 链接混淆、短链和外部引流风险
- 当前分区置顶规则是否仍需要人工核对

## 重要边界

LINUX DO 禁止 AI 生成或润色发帖文字。本项目因此只做离线审查，不会：

- 代写、改写、润色或翻译可直接发布的帖子
- 帮助隐藏 AI 生成痕迹或绕过机器审核
- 自动登录、抓取、监控或发布到 LINUX DO
- 保证帖子一定通过人工审核

审查结果只会列出风险、规则编号和“用户需要自行填写”的信息。

## 使用方式

### 一键安装到 Codex

在 PowerShell、Windows Terminal 或其他终端中运行：

```powershell
npx --yes github:huaxin105820/linuxdo-post-auditor install --force
```

这条命令会从 GitHub 下载最新版本，并将 Skill 直接安装到：

```text
%USERPROFILE%\.codex\skills\linuxdo-post-auditor
```

如果设置了 `CODEX_HOME`，则使用：

```text
%CODEX_HOME%\skills\linuxdo-post-auditor
```

安装或更新完成后，在 Codex 中输入：

```text
使用 $linuxdo-post-auditor 审查我提供的 LINUX DO 发帖草稿。
```

如果 Codex 没有立即识别新安装的 Skill，请重启 Codex。详见 [Codex Skills 官方文档](https://learn.chatgpt.com/docs/build-skills#install-curated-skills-for-local-use)。

### 可选：全局安装 CLI

需要反复安装或更新时，可以先全局安装：

```powershell
npm install --global github:huaxin105820/linuxdo-post-auditor
linuxdo-post-auditor install --force
```

查看默认安装路径：

```powershell
linuxdo-post-auditor path
```

### 在 Codex 中使用

安装后可以直接点名 Skill：

```text
使用 $linuxdo-post-auditor 审查我提供的 LINUX DO 发帖草稿。
```

也可以在 Codex 的 Skills 列表中确认 `linuxdo-post-auditor` 已被发现。

### 使用离线脚本

克隆仓库后，在仓库根目录准备一个 UTF-8 JSON 文件，例如 `draft.json`：

```json
{
  "title": "程序启动失败排查",
  "body": "这里填写由用户自行撰写的完整正文。",
  "category": "开发调优",
  "post_type": "help",
  "tags": ["求助"],
  "links": [],
  "metadata": {
    "environment": "Linux, Python 3.13",
    "attempted": "检查依赖和日志",
    "error_or_symptom": "进程退出",
    "expected": "正常启动",
    "ai_assisted": false
  }
}
```

运行 Markdown 报告：

```powershell
python scripts/audit_draft.py --input draft.json --format markdown
```

运行机器可读的 JSON 报告：

```powershell
python scripts/audit_draft.py --input draft.json --format json
```

## 审核结论

脚本会根据最高风险返回以下状态：

| 状态 | 含义 |
|---|---|
| `DO_NOT_POST` | 存在明确阻断问题，不建议发布 |
| `NEEDS_CHANGES` | 缺少必填项或分区/标签明显不匹配 |
| `MANUAL_REVIEW` | 存在需要结合语境判断的风险 |
| `READY_FOR_MANUAL_REVIEW` | 未发现确定性阻断，但仍需人工核对 |

关键词命中不会自动认定违规。政治、色情、暴力、赌博、欺诈等词语可能出现在技术分析或安全警示中，因此脚本会将这类结果标为人工复核。

## 目录结构

```text
├── SKILL.md                         # Codex 的技能指令
├── package.json                     # npm 包和 CLI 配置
├── bin/cli.js                       # Codex Skill 安装器
├── agents/openai.yaml               # 技能 UI 元数据
├── references/
│   ├── core-rules.md                # 全局规则快照
│   ├── category-rules.json          # 分区用途和匹配规则
│   ├── post-type-checklists.json    # 特殊帖子必填字段
│   ├── pinned-rules.md              # 置顶规则人工录入说明
│   └── rule-sources.md              # 来源和版本记录
├── scripts/
    ├── audit_draft.py               # 离线审核脚本
    └── test_audit_draft.py          # 单元测试
└── test/npm-install.test.js         # npm 安装器测试
```

## 规则维护

当前规则快照记录于 2026-07-27，LINUX DO 指南版本为 `2606081200`。

规则来源：

- [LINUX DO 社区指南](https://linux.do/guidelines)
- [LINUX DO 社区守则](https://wiki.linux.do/LinuxDo/rules)

分区置顶要求可能变化。本项目不自动爬取论坛；维护时请由用户手动提供当前置顶帖内容，并记录来源 URL、主题标题和观察日期。无法确认的分区要求不会凭名称推断。

## 本地验证

```powershell
npm test
python -B -m unittest scripts/test_audit_draft.py
python -X utf8 `
  "C:\Users\Administrator\.codex\skills\.system\skill-creator\scripts\quick_validate.py" `
  .
```

## 许可

本仓库当前未声明开源许可证。除非仓库后续添加许可证文件，否则请不要默认获得再分发或修改授权。
