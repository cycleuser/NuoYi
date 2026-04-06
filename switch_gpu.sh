#!/bin/bash
# GPU切换脚本 - Ubuntu/Linux
# 用于在集成显卡和独立显卡之间切换显示

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}GPU Display Switcher for Ubuntu/Linux${NC}"
echo "============================================"
echo ""

# 检查当前状态
check_current() {
    echo -e "${YELLOW}Current GPU Status:${NC}"
    echo ""
    
    # 检查nvidia-smi
    if command -v nvidia-smi &> /dev/null; then
        echo -e "${GREEN}NVIDIA GPU:${NC}"
        nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv,noheader
        echo ""
    fi
    
    # 检查当前显示
    if command -v glxinfo &> /dev/null; then
        echo -e "${GREEN}Current Display GPU:${NC}"
        glxinfo | grep "OpenGL renderer"
        echo ""
    fi
    
    # 检查prime-select
    if command -v prime-select &> /dev/null; then
        echo -e "${GREEN}NVIDIA Prime Mode:${NC}"
        prime-select query
        echo ""
    fi
}

# 显示菜单
show_menu() {
    echo -e "${YELLOW}Options:${NC}"
    echo "1) Use integrated GPU for display (saves VRAM for computing)"
    echo "2) Use NVIDIA GPU for display (default)"
    echo "3) Check current GPU status"
    echo "4) Exit"
    echo ""
    read -p "Select option [1-4]: " choice
}

# 切换到集成显卡
switch_to_integrated() {
    echo -e "${YELLOW}Switching to integrated GPU for display...${NC}"
    
    if command -v prime-select &> /dev/null; then
        sudo prime-select intel
        echo -e "${GREEN}✓ Switched to integrated GPU${NC}"
        echo -e "${YELLOW}Please log out and log back in for changes to take effect${NC}"
    else
        echo -e "${RED}prime-select not found. Please install NVIDIA drivers:${NC}"
        echo "  sudo apt install nvidia-driver-535  # or latest version"
    fi
}

# 切换到NVIDIA显卡
switch_to_nvidia() {
    echo -e "${YELLOW}Switching to NVIDIA GPU for display...${NC}"
    
    if command -v prime-select &> /dev/null; then
        sudo prime-select nvidia
        echo -e "${GREEN}✓ Switched to NVIDIA GPU${NC}"
        echo -e "${YELLOW}Please log out and log back in for changes to take effect${NC}"
    else
        echo -e "${RED}prime-select not found${NC}"
    fi
}

# 主循环
while true; do
    check_current
    show_menu
    
    case $choice in
        1)
            switch_to_integrated
            break
            ;;
        2)
            switch_to_nvidia
            break
            ;;
        3)
            check_current
            ;;
        4)
            echo "Exiting..."
            break
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            ;;
    esac
done