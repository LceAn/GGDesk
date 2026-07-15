package main

import (
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"unicode"
)

// ScanExeInfo 描述 smart_root 模式下扫描到的候选可执行文件。
// 对应 Python all_exes 列表项：(full_path, file_name, size_bytes, rel_path)。
type ScanExeInfo struct {
	Path    string `json:"path"`
	Name    string `json:"name"`
	Size    int64  `json:"size"`
	RelPath string `json:"relPath"`
}

// rankedExe 记录单个 exe 的评分与原始信息，用于排序。
type rankedExe struct {
	score int
	info  ScanExeInfo
}

var (
	// smartRank 分词用的分隔符正则：下划线/连字符/空格/点。
	tokenSplitter = regexp.MustCompile(`[_\-\s.]+`)
	// 清洁名：去掉分隔符与数字。
	cleanNameRe = regexp.MustCompile(`[_\-\s\d.]+`)
	// 哈希乱码目录：长度>20 且同时含数字和字母且无空格。
	hashDirRe = regexp.MustCompile(`^[^\s]{21,}$`)
)

// smartRankExecutables 对同一目录下的多个 exe 打分排序，返回最优路径的降序列表。
// 完整移植 Python core_discovery.py:66-94 smart_rank_executables。
func smartRankExecutables(programName string, candidates []ScanExeInfo, rootPath string) []ScanExeInfo {
	// 1. 从程序名提取分词 token（长度>1 且非纯数字）。
	tokens := []string{}
	for _, raw := range tokenSplitter.Split(programName, -1) {
		lower := strings.ToLower(raw)
		if len(lower) > 1 && !isAllDigits(lower) {
			tokens = append(tokens, lower)
		}
	}
	cleanName := cleanNameRe.ReplaceAllString(strings.ToLower(programName), "")

	ranked := make([]rankedExe, 0, len(candidates))
	for _, c := range candidates {
		score := 0
		filename := strings.ToLower(c.Name)
		nameNoExt := strings.TrimSuffix(filename, filepath.Ext(filename))

		// 分词匹配：完全相等 +150，包含 +80。
		for _, token := range tokens {
			if token == nameNoExt {
				score += 150
			} else if strings.Contains(nameNoExt, token) {
				score += 80
			}
		}
		// 清洁名匹配。
		if nameNoExt == cleanName {
			score += 100
		} else if cleanName != "" && strings.Contains(nameNoExt, cleanName) {
			score += 50
		}
		// 通用启动器名加分。
		switch nameNoExt {
		case "launcher", "main", "start", "app", "run":
			score += 20
		}
		// 64 位倾向。
		if strings.Contains(nameNoExt, "64") {
			score += 10
		}
		if strings.HasSuffix(filename, ".exe") {
			score += 5
		}
		// 目录深度惩罚：相对 rootPath 的层数 × -15。
		rel := c.RelPath
		depth := strings.Count(rel, string(os.PathSeparator))
		score -= depth * 15

		// 负面关键词：辅助/控制台/服务/工具/崩溃/更新/卸载等。
		negative := []string{"helper", "console", "server", "agent", "service", "tool", "crash", "update", "handler", "uninstall", "eula", "reporter"}
		for _, kw := range negative {
			if strings.Contains(nameNoExt, kw) {
				score -= 100
			}
		}
		ranked = append(ranked, rankedExe{score: score, info: c})
	}

	// 按分数降序；同分按文件名稳定排序。
	sort.SliceStable(ranked, func(i, j int) bool {
		if ranked[i].score != ranked[j].score {
			return ranked[i].score > ranked[j].score
		}
		return strings.ToLower(ranked[i].info.Name) < strings.ToLower(ranked[j].info.Name)
	})

	result := make([]ScanExeInfo, len(ranked))
	for i, r := range ranked {
		result[i] = r.info
	}
	return result
}

// isJunkPath 智能判断路径是否为组件/缓存/运行时目录。
// 移植 Python core_discovery.py:12-29 is_junk_path。
func isJunkPath(path string, badKeywords []string) bool {
	pathLower := strings.ToLower(path)
	folderName := strings.ToLower(filepath.Base(path))

	// 1. 动态关键词匹配。
	for _, kw := range badKeywords {
		kw = strings.TrimSpace(strings.ToLower(kw))
		if kw != "" && strings.Contains(pathLower, kw) {
			return true
		}
	}
	// 2. 哈希/乱码文件夹检测：长度>20 且同时含数字和字母且无空格。
	if len(folderName) > 20 && hashDirRe.MatchString(folderName) &&
		hasDigit(folderName) && hasLowerLetter(folderName) {
		return true
	}
	return false
}

func isAllDigits(s string) bool {
	for _, r := range s {
		if !unicode.IsDigit(r) {
			return false
		}
	}
	return len(s) > 0
}

func hasDigit(s string) bool {
	return strings.ContainsAny(s, "0123456789")
}

func hasLowerLetter(s string) bool {
	return strings.ContainsAny(s, "abcdefghijklmnopqrstuvwxyz")
}
