@echo off
chcp 65001 >nul
title 正在自動下載與安裝畫質提高工具核心組件...
cd /d "%~dp0"
python install_all.py
pause
