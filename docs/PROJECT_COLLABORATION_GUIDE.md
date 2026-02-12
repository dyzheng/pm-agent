# PM Agent 多设备项目协作方案

## 问题分析

`projects/` 目录在 `.gitignore` 中，导致项目数据无法推送到远程仓库，无法在多设备间同步。

---

## 推荐方案对比

### 方案1: 独立Git仓库 ⭐⭐⭐⭐⭐ (最推荐)

**适用场景：**
- 项目需要独立管理
- 不同项目有不同的协作者
- 需要独立的权限控制
- 项目可能独立发展

**优点：**
- ✅ 完全独立，互不干扰
- ✅ 可以有独立的远程仓库
- ✅ 权限控制灵活
- ✅ 可以独立归档/删除

**缺点：**
- ❌ 需要管理多个仓库
- ❌ 需要分别clone/push

**实现步骤：**

```bash
# 1. 进入项目目录
cd /root/pm-agent/projects/f-electron-scf

# 2. 初始化git仓库
git init

# 3. 添加所有文件
git add .

# 4. 创建初始提交
git commit -m "Initial commit: f-electron-scf project with brainstorm optimization

- 27 tasks (19 active + 8 deferred)
- Time saved: 40% (5-6 months vs 7-9 months)
- Interactive dashboard with 5 views
- Complete documentation and plans"

# 5. 添加远程仓库（GitHub/GitLab/Gitee）
git remote add origin https://github.com/your-username/f-electron-scf.git

# 6. 推送到远程
git push -u origin main

# 7. 在其他设备上克隆
cd /root/pm-agent/projects
git clone https://github.com/your-username/f-electron-scf.git
```

**目录结构：**
```
/root/pm-agent/                    # pm-agent主仓库
├── .git/
├── src/
├── tests/
└── projects/                      # 被ignore
    └── f-electron-scf/            # 独立git仓库
        ├── .git/                  # 独立的git
        ├── dashboard.html
        ├── state/
        └── plans/
```

---

### 方案2: 选择性Git追踪 ⭐⭐⭐⭐ (推荐)

**适用场景：**
- 项目是pm-agent的一部分
- 想在pm-agent仓库中统一管理
- 只有少数项目需要追踪

**优点：**
- ✅ 在同一个仓库中管理
- ✅ 统一的版本历史
- ✅ 简单的clone/push流程

**缺点：**
- ❌ 所有协作者都能看到项目
- ❌ 权限控制不灵活

**实现步骤：**

```bash
# 1. 修改.gitignore，改为选择性ignore
cd /root/pm-agent

# 2. 编辑.gitignore
# 将 projects/ 改为 projects/*
# 然后添加 !projects/f-electron-scf/

# 3. 添加项目文件
git add -f projects/f-electron-scf/

# 4. 提交
git commit -m "feat: add f-electron-scf project for multi-device collaboration"

# 5. 推送
git push origin main

# 6. 在其他设备上
git pull origin main
```

**修改后的.gitignore：**
```gitignore
__pycache__/
*.pyc
*.egg-info/
.coverage
.pytest_cache/
state/*.json

# Ignore all projects by default
projects/*

# But track specific projects
!projects/f-electron-scf/

# Ignore project-specific temp files
projects/f-electron-scf/.DS_Store
projects/f-electron-scf/node_modules/
```

---

### 方案3: Git分支管理 ⭐⭐⭐

**适用场景：**
- 想保持main分支干净
- 项目数据较大
- 不想污染主仓库历史

**优点：**
- ✅ 主分支保持干净
- ✅ 项目数据独立分支
- ✅ 可以选择性合并

**缺点：**
- ❌ 分支管理复杂
- ❌ 需要频繁切换分支
- ❌ 容易产生冲突

**实现步骤：**

```bash
# 1. 创建项目分支
cd /root/pm-agent
git checkout -b projects/f-electron-scf

# 2. 在该分支中移除projects/的ignore
# 编辑.gitignore，注释掉 projects/

# 3. 添加项目文件
git add projects/f-electron-scf/
git commit -m "Add f-electron-scf project data"

# 4. 推送项目分支
git push -u origin projects/f-electron-scf

# 5. 切回主分支
git checkout main

# 6. 在其他设备上
git checkout projects/f-electron-scf
git pull origin projects/f-electron-scf
```

**工作流程：**
```bash
# 编辑项目数据
git checkout projects/f-electron-scf
# 修改文件...
git add .
git commit -m "Update project state"
git push

# 编辑pm-agent代码
git checkout main
# 修改代码...
git add .
git commit -m "Update code"
git push
```

---

### 方案4: Git Submodule ⭐⭐

**适用场景：**
- 项目完全独立
- 需要版本锁定
- 多个仓库共享同一个项目

**优点：**
- ✅ 项目完全独立
- ✅ 版本锁定
- ✅ 可以在多个仓库中引用

**缺点：**
- ❌ Submodule管理复杂
- ❌ 容易出错
- ❌ 学习曲线陡峭

**实现步骤：**

```bash
# 1. 先创建独立仓库（参考方案1）
cd /root/pm-agent/projects/f-electron-scf
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/f-electron-scf.git
git push -u origin main

# 2. 在pm-agent中添加为submodule
cd /root/pm-agent
git submodule add https://github.com/your-username/f-electron-scf.git projects/f-electron-scf

# 3. 提交submodule配置
git commit -m "Add f-electron-scf as submodule"
git push

# 4. 在其他设备上
git clone --recursive https://github.com/your-username/pm-agent.git
# 或
git clone https://github.com/your-username/pm-agent.git
cd pm-agent
git submodule init
git submodule update
```

---

## 推荐方案选择

### 场景1: 单人使用，多设备同步
**推荐：方案2（选择性追踪）**
- 最简单
- 统一管理
- 一次push/pull搞定

### 场景2: 团队协作，项目独立
**推荐：方案1（独立仓库）**
- 权限控制灵活
- 项目完全独立
- 可以有不同的协作者

### 场景3: 保持主仓库干净
**推荐：方案3（分支管理）**
- 主分支不受影响
- 项目数据独立分支
- 可选择性合并

---

## 快速实施指南

### 如果选择方案1（独立仓库）：

```bash
#!/bin/bash
# setup_independent_repo.sh

cd /root/pm-agent/projects/f-electron-scf

# 初始化
git init
git add .
git commit -m "Initial commit: f-electron-scf project"

# 添加远程（替换为你的仓库地址）
git remote add origin https://github.com/YOUR_USERNAME/f-electron-scf.git

# 推送
git branch -M main
git push -u origin main

echo "✅ 独立仓库创建完成"
echo "📝 在其他设备上运行："
echo "   cd /root/pm-agent/projects"
echo "   git clone https://github.com/YOUR_USERNAME/f-electron-scf.git"
```

### 如果选择方案2（选择性追踪）：

```bash
#!/bin/bash
# setup_selective_tracking.sh

cd /root/pm-agent

# 备份原.gitignore
cp .gitignore .gitignore.bak

# 修改.gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
*.egg-info/
.coverage
.pytest_cache/
state/*.json

# Ignore all projects by default
projects/*

# But track f-electron-scf
!projects/f-electron-scf/

# Ignore temp files in tracked projects
projects/f-electron-scf/.DS_Store
projects/f-electron-scf/__pycache__/
EOF

# 添加项目
git add -f projects/f-electron-scf/
git commit -m "feat: add f-electron-scf project for multi-device sync"
git push origin main

echo "✅ 选择性追踪设置完成"
echo "📝 在其他设备上运行："
echo "   git pull origin main"
```

---

## 同步工作流

### 方案1（独立仓库）工作流：

```bash
# 设备A：修改项目
cd /root/pm-agent/projects/f-electron-scf
# 修改文件...
git add .
git commit -m "Update task status"
git push

# 设备B：同步
cd /root/pm-agent/projects/f-electron-scf
git pull
```

### 方案2（选择性追踪）工作流：

```bash
# 设备A：修改项目
cd /root/pm-agent
# 修改 projects/f-electron-scf/...
git add projects/f-electron-scf/
git commit -m "Update f-electron-scf project"
git push

# 设备B：同步
cd /root/pm-agent
git pull
```

---

## 建议

**对于f-electron-scf项目，我建议：**

1. **如果只是你个人使用** → 方案2（选择性追踪）
   - 最简单，一次push/pull
   - 统一管理

2. **如果需要团队协作** → 方案1（独立仓库）
   - 权限控制灵活
   - 项目完全独立
   - 可以有独立的issue tracker

3. **如果想保持pm-agent干净** → 方案3（分支管理）
   - 主分支不受影响
   - 项目数据独立

**我的推荐：方案1（独立仓库）**

理由：
- f-electron-scf是一个完整的研究项目
- 有自己的dashboard、文档、状态
- 可能需要独立的协作者
- 未来可能独立发展

---

## 需要我帮你实施吗？

我可以帮你：
1. 创建独立仓库并推送
2. 修改.gitignore实现选择性追踪
3. 创建项目分支
4. 生成同步脚本

你想选择哪个方案？
