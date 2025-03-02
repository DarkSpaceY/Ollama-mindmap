# 思维导图生成器

一个功能强大的思维导图工具，集成了AI自动生成、物理引擎布局等特色功能。

## 主要特性

- 直观的图形界面
  - 美观的节点样式
  - 支持缩放和平移
  - 自定义主题配色

- 智能节点管理
  - 支持节点的添加、编辑、删除
  - 节点展开/收起功能
  - 支持复制粘贴操作
  - 支持撤销/重做

- AI辅助功能
  - 基于LLM的自动内容生成
  - 多种分析模板（SWOT、5W1H等）
  - 支持自定义提示词模板

- 文件操作
  - 支持新建/保存思维导图
  - 导入/导出功能

## 环境要求

- Python 3.9+
- tkinter
- 其他依赖包（见requirements.txt）

## 安装步骤

1. 克隆项目到本地
2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用说明

1. 运行程序：
```bash
python test.py
```

2. 基本操作：
- 左键点击：选择节点
- 拖拽：移动节点
- 右键菜单：访问节点操作
- 工具栏：快捷功能访问

3. AI功能：
- 选择节点后可使用AI自动生成子主题
- 支持多种分析模板
- 可自定义提示词模板

## 主要功能说明

### 节点管理
- 支持多级节点创建
- 节点可自由展开/收起
- 支持节点拖拽定位

### 主题样式
- 提供多套预设主题
- 支持自定义颜色方案
- 节点样式随层级变化

### AI集成
- 集成Ollama LLM模型
- 支持异步生成不卡顿
- 多种分析模板满足不同需求

### 操作历史
- 支持撤销/重做
- 自动保存状态
- 防止误操作

## 注意事项

- 首次使用需要安装并配置Ollama
- 确保系统已安装Python环境
- 推荐使用较新版本的Python
