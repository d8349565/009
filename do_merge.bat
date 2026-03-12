@echo off
chcp 65001 > nul
set WORKTREE=c:\Users\Lee\Documents\代码\009.worktrees\copilot-worktree-2026-03-12T05-23-45
set MAINREPO=c:\Users\Lee\Documents\代码\009
set BRANCH=copilot-worktree-2026-03-12T05-23-45

echo ============================================
echo  Step 1: Fix agents.py Unicode syntax error
echo ============================================
cd /d "%WORKTREE%"
python fix_agents.py
if errorlevel 1 (
    echo ERROR: fix_agents.py failed
    pause
    exit /b 1
)

echo ============================================
echo  Step 2: Delete temp files
echo ============================================
del fix_agents.py 2>nul
del fix_run.js 2>nul

echo ============================================
echo  Step 3: Git commit in worktree
echo ============================================
git add agents.py main.py
git commit -m "fix: 修复搜索词过长导致0结果及无数据时LLM编报告问题

- main.py: 后续迭代从缺失方面提取短关键词(取冒号前核心词,限20字符)
- agents.py: 无数据源时强约束提示词禁止LLM推算编造数据

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
if errorlevel 1 (
    echo ERROR: git commit failed
    pause
    exit /b 1
)

echo ============================================
echo  Step 4: Merge into main repo
echo ============================================
cd /d "%MAINREPO%"
git merge %BRANCH%
if errorlevel 1 (
    echo ERROR: git merge failed
    pause
    exit /b 1
)

echo ============================================
echo  Step 5: Remove worktree and branch
echo ============================================
git worktree remove "%WORKTREE%"
git branch -d %BRANCH%

echo.
echo ============================================
echo  ALL DONE! Merge completed successfully.
echo ============================================
pause

