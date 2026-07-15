DEFAULT_CATEGORY = "默认"

CATEGORY_KEYWORDS = {
    "开发": [
        "code", "cursor", "visual studio", "vscode", "pycharm", "idea", "intellij", "webstorm",
        "datagrip", "phpstorm", "goland", "clion", "rider", "android studio", "github", "git", "python", "node",
        "java", "terminal", "powershell", "xterminal", "postman", "api", "docker", "wsl",
        "ida", "dnspy", "x64dbg", "debug", "dev", "编程", "开发"
    ],
    "AI 工具": [
        "chatgpt", "openai", "claude", "gemini", "ollama", "cherry studio", "trae",
        "cursor", "comet", "copilot", "stable diffusion", "midjourney", "ai studio", "模型"
    ],
    "设计": [
        "figma", "photoshop", "illustrator", "adobe", "blend", "sketch", "affinity",
        "draw", "paint", "canva", "设计", "图片", "图像"
    ],
    "游戏": [
        "steam", "epic", "battle.net", "riot", "minecraft", "game", "launcher",
        "gog", "origin", "ubisoft", "xbox", "游戏"
    ],
    "办公": [
        "office", "word", "excel", "powerpoint", "wps", "onenote", "notion", "typora",
        "obsidian", "yuque", "语雀", "飞书文档", "文档", "表格", "办公"
    ],
    "浏览器": [
        "chrome", "edge", "firefox", "browser", "brave", "opera", "vivaldi", "浏览器"
    ],
    "通讯": [
        "wechat", "weixin", "qq", "discord", "slack", "teams", "telegram", "feishu",
        "飞书", "钉钉", "ding", "zoom", "通讯", "聊天", "会议"
    ],
    "媒体": [
        "music", "video", "player", "vlc", "potplayer", "spotify", "netease", "obs",
        "media", "clipchamp", "音频", "视频", "播放器", "录屏"
    ],
    "云盘": [
        "drive", "netdisk", "onedrive", "dropbox", "aliyun", "baidu", "123pan",
        "cloud", "云盘", "网盘"
    ],
    "安全": [
        "security", "vpn", "clash", "proxy", "defender", "antivirus", "firewall",
        "安全", "代理", "加密"
    ],
    "系统工具": [
        "settings", "control", "tool", "tools", "manager", "cleanup", "config",
        "driver", "printer", "terminal", "cmd", "system", "配置", "管理", "工具",
        "控制", "驱动", "打印"
    ],
}


def suggest_category_for_shortcut(name, exe_path="", source_type=""):
    text = f"{name or ''} {exe_path or ''} {source_type or ''}".lower()
    best_category = DEFAULT_CATEGORY
    best_score = 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in text:
                score += 2 if " " in keyword else 1
        if score > best_score:
            best_category = category
            best_score = score
    return best_category


def suggest_categories_for_shortcuts(shortcuts):
    suggestions = {}
    for row in shortcuts:
        suggestions[row["id"]] = suggest_category_for_shortcut(
            row["name"],
            row["exe_path"],
            row["source_type"]
        )
    return suggestions
