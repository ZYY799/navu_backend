#!/usr/bin/env python3
"""
Git推送工具 - 简化版
"""

import os
import subprocess
import sys
from datetime import datetime

def run_cmd(cmd, show_output=True):
    """运行命令"""
    if show_output:
        print(f"💻 执行: {cmd}")

    result = subprocess.run(
        cmd, 
        shell=True, 
        capture_output=True, 
        text=True, 
        encoding='utf-8'
    )

    if result.returncode != 0 and result.stderr:
        if show_output:
            print(f"❌ 错误: {result.stderr.strip()}")
    elif result.stdout and show_output:
        print(f"✅ 输出: {result.stdout.strip()}")

    return result.returncode, result.stdout, result.stderr

def simple_push():
    """简化的推送流程"""
    print("🚀 Git推送工具")
    print("=" * 50)

    # 1. 检查Git状态
    print("1️⃣ 检查Git状态...")
    code, out, err = run_cmd("git status")
    if code != 0:
        print("❌ 当前目录不是Git仓库")
        return False

    # 2. 显示更改
    print("2️⃣ 显示更改文件...")
    run_cmd("git status --short")

    # 3. 添加文件
    print("3️⃣ 添加文件到暂存区")
    choice = input("选择: 1.全部添加 2.选择文件 3.跳过 (默认1): ").strip() or "1"

    if choice == "1":
        run_cmd("git add -A")
    elif choice == "2":
        # 获取更改的文件列表
        code, out, err = run_cmd("git status --porcelain", show_output=False)
        files = [line[3:] for line in out.strip().split('\n') if line]

        if files:
            print("\n可添加的文件:")
            for i, file in enumerate(files, 1):
                print(f"  {i}. {file}")

            selection = input("输入文件编号（用逗号分隔，或输入'all'全选）: ").strip()

            if selection.lower() == 'all':
                run_cmd("git add -A")
            elif selection:
                for sel in selection.split(','):
                    sel = sel.strip()
                    if sel.isdigit() and 1 <= int(sel) <= len(files):
                        run_cmd(f'git add "{files[int(sel)-1]}"')

    # 4. 提交
    print("\n4️⃣ 提交更改")
    commit_msg = input("输入提交信息（留空使用默认）: ").strip()

    if not commit_msg:
        commit_msg = f"更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    code, out, err = run_cmd(f'git commit -m "{commit_msg}"')
    if code != 0:
        print("❌ 提交失败")
        return False

    # 5. 推送
    print("\n5️⃣ 推送到远程仓库")
    branch = input("输入分支名（默认: main）: ").strip() or "main"

    print(f"📤 正在推送到 {branch} 分支...")
    code, out, err = run_cmd(f"git push origin {branch}")

    if code != 0:
        print("❌ 推送失败")
        retry = input("是否尝试先拉取更新？(y/N): ").strip().lower()
        if retry == 'y':
            run_cmd("git pull --rebase")
            run_cmd(f"git push origin {branch}")
        else:
            force = input("是否强制推送？(y/N): ").strip().lower()
            if force == 'y':
                run_cmd(f"git push origin {branch} --force")

    # 6. 显示结果
    print("\n" + "=" * 50)
    print("📊 推送完成！")
    print("当前状态:")
    run_cmd("git status")

    return True

if __name__ == "__main__":
    simple_push()
