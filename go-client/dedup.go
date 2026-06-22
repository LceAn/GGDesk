package main

import (
	"math"
	"path/filepath"
	"sort"
	"strings"
)

type DuplicateItem struct {
	ID         int64  `json:"id"`
	Name       string `json:"name"`
	ExePath    string `json:"exePath"`
	LnkPath    string `json:"lnkPath"`
	SourceType string `json:"sourceType"`
	Category   string `json:"category"`
	RunCount   int    `json:"runCount"`
	Score      int    `json:"score"`
	Keep       bool   `json:"keep"`
}

type DuplicateGroup struct {
	Key    string          `json:"key"`
	Items  []DuplicateItem `json:"items"`
	Reason string          `json:"reason"`
}

type DedupResult struct {
	Groups []DuplicateGroup `json:"groups"`
	Total  int              `json:"total"`
}

func (a *App) AnalyzeDuplicates(threshold float64) (DedupResult, error) {
	if threshold <= 0 || threshold > 1 {
		threshold = 0.6
	}
	shortcuts, err := a.ListShortcuts(ShortcutFilter{SortBy: "name"})
	if err != nil {
		return DedupResult{}, err
	}
	items := make([]DuplicateItem, 0, len(shortcuts))
	for _, s := range shortcuts {
		items = append(items, DuplicateItem{
			ID:         s.ID,
			Name:       s.Name,
			ExePath:    s.ExePath,
			LnkPath:    s.LnkPath,
			SourceType: s.SourceType,
			Category:   s.Category,
			RunCount:   s.RunCount,
			Score:      duplicateScore(s),
		})
	}

	groups := exactDuplicateGroups(items)
	used := map[int64]bool{}
	for _, group := range groups {
		for _, item := range group.Items {
			used[item.ID] = true
		}
	}

	for i := 0; i < len(items); i++ {
		if used[items[i].ID] {
			continue
		}
		group := []DuplicateItem{items[i]}
		for j := i + 1; j < len(items); j++ {
			if used[items[j].ID] {
				continue
			}
			if looksSimilar(items[i], items[j], threshold) {
				group = append(group, items[j])
				used[items[j].ID] = true
			}
		}
		if len(group) > 1 {
			groups = append(groups, markKeeper(DuplicateGroup{
				Key:    strings.ToLower(items[i].Name),
				Items:  group,
				Reason: "名称或路径相似",
			}))
		}
	}

	sort.SliceStable(groups, func(i, j int) bool {
		return strings.ToLower(groups[i].Key) < strings.ToLower(groups[j].Key)
	})
	total := 0
	for _, group := range groups {
		total += len(group.Items)
	}
	return DedupResult{Groups: groups, Total: total}, nil
}

func (a *App) RemoveDuplicateShortcuts(ids []int64) (int, error) {
	if err := a.ensureDB(); err != nil {
		return 0, err
	}
	tx, err := a.db.Begin()
	if err != nil {
		return 0, err
	}
	defer tx.Rollback()
	count := 0
	for _, id := range ids {
		res, err := tx.Exec(`DELETE FROM shortcuts WHERE id = ?`, id)
		if err != nil {
			return count, err
		}
		n, _ := res.RowsAffected()
		count += int(n)
	}
	return count, tx.Commit()
}

func exactDuplicateGroups(items []DuplicateItem) []DuplicateGroup {
	byName := map[string][]DuplicateItem{}
	byTarget := map[string][]DuplicateItem{}
	for _, item := range items {
		nameKey := normalizeText(item.Name)
		targetKey := normalizeTarget(firstNonEmpty(item.ExePath, item.LnkPath))
		if nameKey != "" {
			byName[nameKey] = append(byName[nameKey], item)
		}
		if targetKey != "" {
			byTarget[targetKey] = append(byTarget[targetKey], item)
		}
	}
	groups := []DuplicateGroup{}
	seen := map[int64]bool{}
	for key, group := range byTarget {
		if len(group) > 1 {
			groups = append(groups, markKeeper(DuplicateGroup{Key: key, Items: group, Reason: "目标路径相同"}))
			for _, item := range group {
				seen[item.ID] = true
			}
		}
	}
	for key, group := range byName {
		filtered := []DuplicateItem{}
		for _, item := range group {
			if !seen[item.ID] {
				filtered = append(filtered, item)
			}
		}
		if len(filtered) > 1 {
			groups = append(groups, markKeeper(DuplicateGroup{Key: key, Items: filtered, Reason: "名称相同"}))
		}
	}
	return groups
}

func markKeeper(group DuplicateGroup) DuplicateGroup {
	sort.SliceStable(group.Items, func(i, j int) bool {
		if group.Items[i].Score != group.Items[j].Score {
			return group.Items[i].Score > group.Items[j].Score
		}
		return group.Items[i].RunCount > group.Items[j].RunCount
	})
	for i := range group.Items {
		group.Items[i].Keep = i == 0
	}
	return group
}

func duplicateScore(s Shortcut) int {
	score := s.RunCount
	switch s.SourceType {
	case "custom":
		score += 30
	case "uwp":
		score += 20
	case "start_menu":
		score += 10
	}
	if s.LnkPath != "" {
		score += 5
	}
	if s.Category != "" && s.Category != defaultCategory {
		score += 5
	}
	return score
}

func looksSimilar(a, b DuplicateItem, threshold float64) bool {
	nameA := normalizeText(a.Name)
	nameB := normalizeText(b.Name)
	if nameA == "" || nameB == "" {
		return false
	}
	if strings.Contains(nameA, nameB) || strings.Contains(nameB, nameA) {
		return true
	}
	if similarityRatio(nameA, nameB) >= threshold {
		return true
	}
	pathA := strings.ToLower(filepath.Dir(firstNonEmpty(a.ExePath, a.LnkPath)))
	pathB := strings.ToLower(filepath.Dir(firstNonEmpty(b.ExePath, b.LnkPath)))
	if len(commonPrefix(pathA, pathB)) > 8 && similarityRatio(nameA, nameB) >= threshold-0.12 {
		return true
	}
	return false
}

func similarityRatio(a, b string) float64 {
	if a == b {
		return 1
	}
	if a == "" || b == "" {
		return 0
	}
	distance := levenshtein(a, b)
	maxLen := math.Max(float64(len([]rune(a))), float64(len([]rune(b))))
	return 1 - float64(distance)/maxLen
}

func levenshtein(a, b string) int {
	ar := []rune(a)
	br := []rune(b)
	prev := make([]int, len(br)+1)
	for j := range prev {
		prev[j] = j
	}
	for i, ca := range ar {
		current := make([]int, len(br)+1)
		current[0] = i + 1
		for j, cb := range br {
			cost := 0
			if ca != cb {
				cost = 1
			}
			current[j+1] = minInt(current[j]+1, prev[j+1]+1, prev[j]+cost)
		}
		prev = current
	}
	return prev[len(br)]
}

func minInt(values ...int) int {
	best := values[0]
	for _, value := range values[1:] {
		if value < best {
			best = value
		}
	}
	return best
}

func normalizeText(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	replacer := strings.NewReplacer(" ", "", "-", "", "_", "", ".", "", "(", "", ")", "")
	return replacer.Replace(value)
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return ""
}

func commonPrefix(a, b string) string {
	n := minInt(len(a), len(b))
	i := 0
	for i < n && a[i] == b[i] {
		i++
	}
	return a[:i]
}
