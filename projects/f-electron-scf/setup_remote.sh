#!/bin/bash
# Setup script for f-electron-scf project remote repository

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║         f-electron-scf 独立仓库设置脚本                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if we're in the right directory
if [ ! -f "dashboard.html" ]; then
    echo "❌ 错误：请在 f-electron-scf 项目目录中运行此脚本"
    echo "   cd /root/pm-agent/projects/f-electron-scf"
    exit 1
fi

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ 错误：Git 仓库未初始化"
    echo "   运行: git init"
    exit 1
fi

echo "📝 请选择远程仓库平台："
echo "   1) GitHub"
echo "   2) GitLab"
echo "   3) Gitee (码云)"
echo "   4) 自定义 URL"
echo ""
read -p "选择 (1-4): " choice

case $choice in
    1)
        read -p "GitHub 用户名: " username
        read -p "仓库名 (默认: f-electron-scf): " repo
        repo=${repo:-f-electron-scf}
        remote_url="https://github.com/$username/$repo.git"
        ;;
    2)
        read -p "GitLab 用户名: " username
        read -p "仓库名 (默认: f-electron-scf): " repo
        repo=${repo:-f-electron-scf}
        remote_url="https://gitlab.com/$username/$repo.git"
        ;;
    3)
        read -p "Gitee 用户名: " username
        read -p "仓库名 (默认: f-electron-scf): " repo
        repo=${repo:-f-electron-scf}
        remote_url="https://gitee.com/$username/$repo.git"
        ;;
    4)
        read -p "远程仓库 URL: " remote_url
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 配置信息："
echo "   远程仓库: $remote_url"
echo "   本地分支: main"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "确认推送？(y/n): " confirm

if [ "$confirm" != "y" ]; then
    echo "❌ 已取消"
    exit 0
fi

echo ""
echo "🚀 开始设置远程仓库..."

# Add remote
if git remote | grep -q "^origin$"; then
    echo "⚠️  远程仓库 'origin' 已存在，正在更新..."
    git remote set-url origin "$remote_url"
else
    git remote add origin "$remote_url"
fi

echo "✅ 远程仓库已添加"

# Push to remote
echo ""
echo "📤 推送到远程仓库..."
if git push -u origin main; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ 成功！f-electron-scf 项目已推送到远程仓库"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📊 项目信息："
    echo "   • 总任务数: 27"
    echo "   • 活跃任务: 19"
    echo "   • 延迟任务: 8"
    echo "   • 预计时间: 5-6个月"
    echo "   • 节省时间: 40%"
    echo ""
    echo "🌐 远程仓库: $remote_url"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 在其他设备上克隆："
    echo "   cd /root/pm-agent/projects"
    echo "   git clone $remote_url"
    echo ""
    echo "🔄 同步更新："
    echo "   git pull origin main"
    echo ""
    echo "📤 推送更改："
    echo "   git add ."
    echo "   git commit -m \"Update task status\""
    echo "   git push origin main"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  推送失败"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "可能的原因："
    echo "   1. 远程仓库不存在 - 请先在 GitHub/GitLab/Gitee 上创建仓库"
    echo "   2. 没有推送权限 - 检查 SSH key 或访问令牌"
    echo "   3. 网络问题 - 检查网络连接"
    echo ""
    echo "💡 手动推送："
    echo "   1. 在 GitHub/GitLab/Gitee 上创建名为 'f-electron-scf' 的仓库"
    echo "   2. 运行: git push -u origin main"
    echo ""
fi
