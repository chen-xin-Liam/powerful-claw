# 主题配置系统

## 🎨 概述

本项目支持自定义主题配置，用户可以通过创建 `.ini` 配置文件来自定义界面颜色。

## 📂 主题配置目录

```
config/
└── themes/
    ├── ocean_blue.ini          # 海洋蓝主题（默认）
    ├── forest_green.ini        # 森林绿主题
    ├── sunset_orange.ini       # 日落橙主题
    ├── purple_dream.ini        # 紫色梦幻主题
    ├── crimson_red.ini         # 深红主题
    ├── silver_gray.ini         # 银灰色主题
    ├── cyber_yellow.ini        # 赛博黄主题
    ├── deep_space.ini          # 深空主题
    └── theme_example.ini       # 配置示例文件
```

## ✏️ 创建自定义主题

### 方法一：复制修改示例文件

1. 复制 `theme_example.ini` 并重命名
2. 修改配置内容
3. 将文件放入 `config/themes/` 目录
4. 重启应用即可在主题列表中看到新主题

### 方法二：拖放加载

将自定义的 `.ini` 文件拖放到应用窗口，自动加载并添加到主题列表。

## 📋 配置文件格式

```ini
[Theme]
name=主题名称
author=作者
version=1.0
description=主题描述

[Colors]
primary=#1E90FF
secondary=#00BFFF
accent=#87CEEB
background=#0A192F
surface=#112240
card=#1A365D
border=#2D4A6F
text_primary=#FFFFFF
text_secondary=#94A3B8
text_disabled=#475569
success=#10B981
warning=#F59E0B
error=#EF4444
info=#3B82F6
```

### 颜色说明

| 颜色项 | 用途 |
|--------|------|
| `primary` | 主色调，用于按钮、链接等 |
| `secondary` | 次要颜色 |
| `accent` | 强调颜色 |
| `background` | 主背景色 |
| `surface` | 表面背景色 |
| `card` | 卡片背景色 |
| `border` | 边框颜色 |
| `text_primary` | 主要文字颜色 |
| `text_secondary` | 次要文字颜色 |
| `text_disabled` | 禁用状态文字颜色 |
| `success` | 成功状态颜色 |
| `warning` | 警告状态颜色 |
| `error` | 错误状态颜色 |
| `info` | 信息提示颜色 |

## 🎯 预设主题

| 主题名称 | 主色调 | 描述 |
|----------|--------|------|
| Ocean Blue | #1E90FF | 海洋蓝主题，清新自然 |
| Forest Green | #22C55E | 森林绿主题，自然清新 |
| Sunset Orange | #F97316 | 日落橙主题，温暖热情 |
| Purple Dream | #8B5CF6 | 紫色梦幻主题，神秘优雅 |
| Crimson Red | #DC2626 | 深红主题，热烈激情 |
| Silver Gray | #6B7280 | 银灰色主题，简约商务 |
| Cyber Yellow | #EAB308 | 赛博黄主题，科技感十足 |
| Deep Space | #6366F1 | 深空主题，神秘深邃 |

## 💡 注意事项

1. 配置文件必须以 `.ini` 为扩展名
2. 颜色值必须是有效的十六进制颜色代码（如 #RRGGBB）
3. 文件编码必须为 UTF-8
4. 修改主题后需要重启应用生效
5. 主题名称不能重复

## 📁 主题管理器 API

```python
from src.config import theme_manager

# 加载所有主题
theme_manager.load_all_themes()

# 获取所有主题名称
themes = theme_manager.get_theme_names()

# 设置当前主题
theme_manager.set_theme("Ocean Blue")

# 添加主题（拖放加载）
theme_manager.add_theme_from_file("path/to/theme.ini")

# 创建新主题
new_theme = ThemeConfig(
    name="My Theme",
    author="Me",
    colors=ThemeColors(primary="#FF0000")
)
theme_manager.create_theme(new_theme)

# 删除主题
theme_manager.remove_theme("My Theme")

# 导出主题
theme_manager.export_theme("Ocean Blue", "exported_theme.ini")
```
