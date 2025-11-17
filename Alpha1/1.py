import os
import win32com.client  # 导入我们刚刚安装的库
import time

# --- 1. 配置项 (你只需要修改这里) ---

# 【请修改】你要扫描的路径 (r'' 是为了防止路径中的 \ 被转义)
PATH_TO_SCAN = r"D:\Win\JetBrains"

# 【请修改】输出文件夹的名称 (它将被创建在桌面上)
OUTPUT_FOLDER_NAME = "MyTestShortcuts"

# -------------------------------------


def create_shortcut(target_path, shortcut_path):
    """
    使用 win32com 创建一个 .lnk 快捷方式
    
    :param target_path: 目标.exe的完整路径
    :param shortcut_path: 要创建的.lnk快捷方式的完整路径
    """
    try:
        # 获取 WScript.Shell COM 对象
        shell = win32com.client.Dispatch("WScript.Shell")
        
        # 创建快捷方式对象
        shortcut = shell.CreateShortCut(shortcut_path)
        
        # 设置快捷方式的核心属性
        shortcut.TargetPath = target_path
        
        # 关键！设置工作目录。
        # 很多程序(特别是游戏)需要这个，否则它们启动时找不到资源文件。
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        
        # (可选) 设置图标为.exe文件本身
        shortcut.IconLocation = target_path
        
        # 保存快捷方式
        shortcut.Save()
        
    except Exception as e:
        print(f"  [!] 创建失败: {os.path.basename(shortcut_path)} | 错误: {e}")

def main_scanner():
    """
    主扫描逻辑
    """
    print(f"--- 启动扫描器 ---")
    
    # 1. 确定桌面和输出文件夹的路径
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    shortcut_dir = os.path.join(desktop_path, OUTPUT_FOLDER_NAME)

    # 2. 如果文件夹不存在，则创建它 (防止你说的“桌面一大堆”)
    if not os.path.exists(shortcut_dir):
        os.makedirs(shortcut_dir)
        print(f"已创建输出文件夹: {shortcut_dir}")
    else:
        print(f"快捷方式将输出至: {shortcut_dir}")

    # 3. 递归扫描目标路径
    print(f"\n开始扫描: {PATH_TO_SCAN}\n")
    found_count = 0
    
    # os.walk 会递归遍历所有子文件夹
    for root, dirs, files in os.walk(PATH_TO_SCAN):
        for file in files:
            # 检查是否为 .exe 文件 (不区分大小写)
            if file.lower().endswith(".exe"):
                found_count += 1
                
                # 构造完整路径
                exe_full_path = os.path.join(root, file)
                
                # 构造快捷方式的名称和完整路径
                shortcut_name = f"{os.path.splitext(file)[0]}.lnk"
                shortcut_full_path = os.path.join(shortcut_dir, shortcut_name)
                
                # 4. 创建快捷方式
                print(f"  [+] 找到: {file}")
                create_shortcut(exe_full_path, shortcut_full_path)

    # 5. 结束
    print("\n--- 扫描完成 ---")
    if found_count == 0:
        print(f"在 {PATH_TO_SCAN} 及其子目录中未找到 .exe 文件。")
    else:
        print(f"总共找到 {found_count} 个 .exe 文件。快捷方式已在桌面 '{OUTPUT_FOLDER_NAME}' 文件夹中生成。")


if __name__ == "__main__":
    # 确保我们是在 Windows 上运行
    if os.name != 'nt':
        print("错误：此脚本需要 Windows (pywin32) 环境来创建 .lnk 快捷方式。")
    else:
        main_scanner()
        
    # (可选) 暂停5秒，防止窗口一闪而过
    time.sleep(5)