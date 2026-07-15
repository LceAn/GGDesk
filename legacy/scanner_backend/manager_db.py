import sqlite3

from .const import DB_FILE_CACHE, DB_FILE_USER


DEFAULT_CATEGORY = "默认"


def init_databases():
    """初始化用户数据与缓存数据库。"""
    try:
        _init_user_db()
        _init_cache_db()
        return True, "数据库初始化成功"
    except Exception as e:
        return False, f"数据库初始化失败: {e}"


def _init_user_db():
    conn = sqlite3.connect(DB_FILE_USER)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS shortcuts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    exe_path TEXT,
                    lnk_path TEXT,
                    args TEXT,
                    icon_path TEXT,
                    source_type TEXT,
                    category TEXT DEFAULT '默认',
                    run_count INTEGER DEFAULT 0,
                    is_pinned BOOLEAN DEFAULT 0,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
    _ensure_shortcuts_schema(c)
    c.execute('''CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    sort_order INTEGER DEFAULT 0
                )''')
    c.execute("INSERT OR IGNORE INTO categories (name, sort_order) VALUES (?, ?)", (DEFAULT_CATEGORY, 0))
    c.execute("UPDATE shortcuts SET category = ? WHERE category IS NULL OR TRIM(category) = ''", (DEFAULT_CATEGORY,))
    c.execute("SELECT DISTINCT category FROM shortcuts WHERE category IS NOT NULL AND TRIM(category) != ''")
    for row in c.fetchall():
        _ensure_category(c, row[0])
    conn.commit()
    conn.close()


def _ensure_shortcuts_schema(cursor):
    cursor.execute("PRAGMA table_info(shortcuts)")
    columns = {row[1] for row in cursor.fetchall()}
    if "category" not in columns:
        cursor.execute("ALTER TABLE shortcuts ADD COLUMN category TEXT DEFAULT '默认'")


def _init_cache_db():
    conn = sqlite3.connect(DB_FILE_CACHE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS icon_cache (
                    file_path TEXT PRIMARY KEY,
                    icon_blob BLOB,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
    conn.commit()
    conn.close()


def _ensure_category(cursor, name):
    clean = (name or DEFAULT_CATEGORY).strip() or DEFAULT_CATEGORY
    cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (clean,))
    return clean


def add_shortcut_to_db(name, exe_path, lnk_path, source_type, args="", category=None):
    """添加或更新一个快捷方式。"""
    conn = sqlite3.connect(DB_FILE_USER)
    c = conn.cursor()
    try:
        category = _ensure_category(c, category)
        c.execute("SELECT id FROM shortcuts WHERE exe_path = ?", (exe_path,))
        data = c.fetchone()
        if data:
            c.execute(
                "UPDATE shortcuts SET name=?, lnk_path=?, source_type=?, args=?, category=? WHERE id=?",
                (name, lnk_path, source_type, args, category, data[0])
            )
        else:
            c.execute(
                "INSERT INTO shortcuts (name, exe_path, lnk_path, source_type, args, category) VALUES (?, ?, ?, ?, ?, ?)",
                (name, exe_path, lnk_path, source_type, args, category)
            )
        conn.commit()
        return True
    except Exception as e:
        print(f"DB Error: {e}")
        return False
    finally:
        conn.close()


def get_all_shortcuts(category=None):
    """获取所有快捷方式，可按分类过滤。"""
    conn = sqlite3.connect(DB_FILE_USER)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if category and category != "全部":
        c.execute("SELECT * FROM shortcuts WHERE category = ? ORDER BY added_at DESC", (category,))
    else:
        c.execute("SELECT * FROM shortcuts ORDER BY added_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows


def delete_shortcut(shortcut_id):
    conn = sqlite3.connect(DB_FILE_USER)
    c = conn.cursor()
    c.execute("DELETE FROM shortcuts WHERE id = ?", (shortcut_id,))
    conn.commit()
    conn.close()


def increment_run_count(shortcut_id):
    conn = sqlite3.connect(DB_FILE_USER)
    c = conn.cursor()
    c.execute("UPDATE shortcuts SET run_count = run_count + 1 WHERE id = ?", (shortcut_id,))
    conn.commit()
    conn.close()


def get_categories(include_all=False):
    conn = sqlite3.connect(DB_FILE_USER)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT name FROM categories ORDER BY sort_order ASC, name COLLATE NOCASE ASC")
    names = [row["name"] for row in c.fetchall()]
    c.execute("SELECT DISTINCT category FROM shortcuts WHERE category IS NOT NULL AND category != ''")
    for row in c.fetchall():
        if row["category"] not in names:
            names.append(row["category"])
    conn.close()
    if DEFAULT_CATEGORY not in names:
        names.insert(0, DEFAULT_CATEGORY)
    return ["全部"] + names if include_all else names


def add_category(name):
    conn = sqlite3.connect(DB_FILE_USER)
    c = conn.cursor()
    try:
        clean = _ensure_category(c, name)
        conn.commit()
        return True, clean
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def rename_category(old_name, new_name):
    old_clean = (old_name or "").strip()
    new_clean = (new_name or "").strip()
    if not old_clean or not new_clean:
        return False, "分类名称不能为空"
    if old_clean == DEFAULT_CATEGORY:
        return False, "默认分类不能重命名"
    conn = sqlite3.connect(DB_FILE_USER)
    c = conn.cursor()
    try:
        _ensure_category(c, new_clean)
        c.execute("DELETE FROM categories WHERE name = ?", (old_clean,))
        c.execute("UPDATE shortcuts SET category = ? WHERE category = ?", (new_clean, old_clean))
        conn.commit()
        return True, new_clean
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def delete_category(name, fallback=DEFAULT_CATEGORY):
    clean = (name or "").strip()
    if not clean:
        return False, "分类名称不能为空"
    if clean == DEFAULT_CATEGORY:
        return False, "默认分类不能删除"
    conn = sqlite3.connect(DB_FILE_USER)
    c = conn.cursor()
    try:
        fallback = _ensure_category(c, fallback)
        c.execute("UPDATE shortcuts SET category = ? WHERE category = ?", (fallback, clean))
        c.execute("DELETE FROM categories WHERE name = ?", (clean,))
        conn.commit()
        return True, clean
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def update_shortcut_category(shortcut_id, category):
    conn = sqlite3.connect(DB_FILE_USER)
    c = conn.cursor()
    try:
        category = _ensure_category(c, category)
        c.execute("UPDATE shortcuts SET category = ? WHERE id = ?", (category, shortcut_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB Error: {e}")
        return False
    finally:
        conn.close()
