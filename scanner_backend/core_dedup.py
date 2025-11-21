import os
import difflib
from collections import defaultdict


class DuplicateAnalyzer:
    def __init__(self, threshold=0.6):
        """
        threshold: 相似度阈值 (0.0 - 1.0)，越高越严格
        """
        self.threshold = threshold

    def analyze(self, program_list):
        """
        分析程序列表，返回:
        1. unique_items: 确定的唯一项 (包含自动合并的精确重复)
        2. fuzzy_groups: 疑似重复组 [[item1, item2], [item3, item4]]
        """
        # 1. 精确去重 (Exact Match) - 自动合并
        # 策略：同名且同路径(normalized) -> 视为同一文件
        # 策略：同名但不同源 -> 保留高优先级源 (Custom > UWP > StartMenu)
        exact_map = {}
        source_priority = {'custom': 3, 'uwp': 2, 'start_menu': 1}

        for p in program_list:
            # Key: (Name_Lower)
            key = p['name'].lower()

            if key in exact_map:
                existing = exact_map[key]
                # 比较源优先级
                old_p = source_priority.get(existing.get('type', 'custom'), 0)
                new_p = source_priority.get(p.get('type', 'custom'), 0)

                if new_p > old_p:
                    exact_map[key] = p  # 替换
                # 如果优先级相同（比如两个自定义目录扫到了同名文件），保留第一个，或者视为Fuzzy？
                # 这里简单处理：同名视为精确重复，保留一个。
            else:
                exact_map[key] = p

        unique_candidates = list(exact_map.values())

        # 2. 模糊去重 (Fuzzy Match) - 也就是你要求的路径+名称分析
        # 复杂度 O(N^2)，但通常扫描结果在几百以内，可接受
        # 我们使用并查集 (Union-Find) 思想或者简单的聚类来分组

        visited = set()
        fuzzy_groups = []
        final_unique = []

        # 按路径排序，增加邻近性检查的命中率
        unique_candidates.sort(key=lambda x: x['root_path'])

        for i in range(len(unique_candidates)):
            if i in visited: continue

            current = unique_candidates[i]
            group = [current]
            visited.add(i)

            for j in range(i + 1, len(unique_candidates)):
                if j in visited: continue

                candidate = unique_candidates[j]

                # 执行相似度检查
                if self._is_similar(current, candidate):
                    group.append(candidate)
                    visited.add(j)

            if len(group) > 1:
                fuzzy_groups.append(group)
            else:
                final_unique.append(group[0])

        return final_unique, fuzzy_groups

    def _is_similar(self, p1, p2):
        # 1. 路径相似度分析
        # 如果两个程序在同一个父目录下 (比如 /123/456/A.exe 和 /123/567/B.exe)
        # 计算公共路径长度
        path1 = os.path.normpath(p1['root_path']).lower()
        path2 = os.path.normpath(p2['root_path']).lower()

        # 如果完全不在一个盘符或差异巨大，直接False
        common = os.path.commonprefix([path1, path2])
        if len(common) < 5:  # 公共路径太短
            return False

        # 2. 名称相似度分析 (A.exe vs A_B.exe)
        name1 = p1['name'].lower()
        name2 = p2['name'].lower()

        # 包含关系 (A in A_B)
        if name1 in name2 or name2 in name1:
            return True

        # 序列相似度 (Levenshtein)
        ratio = difflib.SequenceMatcher(None, name1, name2).ratio()
        if ratio > self.threshold:
            return True

        return False


# 暴露的简单接口
def deduplicate_programs(program_list):
    # 为了兼容旧代码调用，这里只做精确去重，不做模糊
    # 模糊去重需要 UI 介入，由前端控制
    analyzer = DuplicateAnalyzer()
    unique, _ = analyzer.analyze(program_list)
    return unique