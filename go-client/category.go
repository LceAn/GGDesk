package main

import "strings"

// categoryRule 定义一个分类及其触发关键词。
type categoryRule struct {
	name     string
	keywords []string
}

// categoryRules 合并 Python category_ai.py 与原 Go 版的关键词表，
// 并保留中文词以提升本地化匹配率。顺序即优先级（开发优先于 AI 工具等）。
var categoryRules = []categoryRule{
	{"开发", []string{"code", "cursor", "codex", "visual studio", "vscode", "goland", "pycharm", "webstorm", "datagrip", "idea", "intellij", "phpstorm", "clion", "rider", "android studio", "github", "git", "node", "python", "go.exe", "java.exe", "javaw", "docker", "wsl", "terminal", "powershell", "cmd", "postman", "api", "ida", "dnspy", "x64dbg", "dev", "编程", "开发"}},
	{"AI 工具", []string{"chatgpt", "openai", "claude", "gemini", "copilot", "ollama", "cherry studio", "trae", "comet", "stable diffusion", "comfyui", "midjourney", "ai studio", "模型"}},
	{"设计", []string{"figma", "photoshop", "illustrator", "adobe", "blend", "sketch", "affinity", "draw", "paint", "canva", "xd", "creator", "设计", "图片", "图像"}},
	{"游戏", []string{"steam", "epic", "battle.net", "riot", "minecraft", "game", "gaming", "gog", "origin", "ubisoft", "xbox", "游戏"}},
	{"办公", []string{"office", "word", "excel", "powerpoint", "wps", "onenote", "outlook", "notion", "typora", "obsidian", "yuque", "语雀", "飞书文档", "pdf", "文档", "表格", "办公"}},
	{"浏览器", []string{"chrome", "edge", "firefox", "browser", "arc", "brave", "opera", "vivaldi", "浏览器"}},
	{"通讯", []string{"wechat", "weixin", "qq", "discord", "slack", "teams", "telegram", "feishu", "飞书", "钉钉", "ding", "zoom", "通讯", "聊天", "会议"}},
	{"媒体", []string{"music", "video", "player", "vlc", "potplayer", "spotify", "netease", "obs", "media", "clipchamp", "photos", "zune", "音频", "视频", "播放器", "录屏", "照片"}},
	{"云盘", []string{"drive", "netdisk", "onedrive", "dropbox", "icloud", "synology", "aliyun", "baidu", "123pan", "cloud", "云盘", "网盘"}},
	{"安全", []string{"security", "vpn", "clash", "proxy", "defender", "antivirus", "firewall", "1password", "password", "authenticator", "安全", "代理", "加密"}},
	{"系统工具", []string{"settings", "control", "tool", "tools", "manager", "cleanup", "config", "printer", "system", "disk", "cmd", "powershell", "管理", "配置", "工具", "控制", "驱动", "打印", "终端", "诊断"}},
}

// SuggestCategory 对单个快捷方式给出分类建议。
// 移植 Python category_ai.py 的累计打分：多关键词累计，含空格关键词 ×2 权重，取最高分。
// 超越旧版"首个命中即返回"的短路逻辑，准确度更高。
func SuggestCategory(name, exePath, sourceType string) string {
	text := strings.ToLower(strings.TrimSpace(name + " " + exePath + " " + sourceType))
	if text == "" {
		return defaultCategory
	}

	bestCategory := defaultCategory
	bestScore := 0
	for _, rule := range categoryRules {
		score := 0
		for _, keyword := range rule.keywords {
			kw := strings.ToLower(keyword)
			if kw == "" {
				continue
			}
			if strings.Contains(text, kw) {
				// 含空格的多词关键词（如 "visual studio"）权重更高。
				if strings.Contains(kw, " ") {
					score += 2
				} else {
					score += 1
				}
			}
		}
		if score > bestScore {
			bestScore = score
			bestCategory = rule.name
		}
	}
	return bestCategory
}
