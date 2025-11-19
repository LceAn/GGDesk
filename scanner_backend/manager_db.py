import sqlite3
import os
from .const import DB_FILE_USER, DB_FILE_CACHE

def init_databases():
    """初始化两个 SQLite 数据库及其表结构"""
    try:
        _init_user_db()
        _init_cache_db()
        return True, "数据库初始化成功"
    except Exception as e:
        return False, f"数据库初始化失败: {e}"

def _init_user_db():
    conn = sqlite3.connect(DB_FILE_USER)
    c = conn.cursor()
    # 快捷方式表
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
    # 分类表
    c.execute('''CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    sort_order INTEGER DEFAULT 0
                )''')
    conn.commit(); conn.close()

def _init_cache_db():
    conn = sqlite3.connect(DB_FILE_CACHE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS icon_cache (
                    file_path TEXT PRIMARY KEY,
                    icon_blob BLOB,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
    conn.commit(); conn.close()

# --- 【Beta 7.0 新增】 CRUD 操作 ---

def add_shortcut_to_db(name, exe_path, lnk_path, source_type, args=""):
    """添加一个快捷方式到数据库"""
    conn = sqlite3.connect(DB_FILE_USER)
    c = conn.cursor()
    try:
        # 简单的查重：如果 exe_path 相同，则更新
        c.execute("SELECT id FROM shortcuts WHERE exe_path = ?", (exe_path,))
        data = c.fetchone()
        if data:
            # 更新
            c.execute("UPDATE shortcuts SET name=?, lnk_path=?, source_type=?, args=? WHERE id=?",
                      (name, lnk_path, source_type, args, data[0]))
        else:
            # 插入
            c.execute("INSERT INTO shortcuts (name, exe_path, lnk_path, source_type, args) VALUES (?, ?, ?, ?, ?)",
                      (name, exe_path, lnk_path, source_type, args))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB Error: {e}")
        return False
    finally:
        conn.close()

def get_all_shortcuts():
    """获取所有快捷方式"""
    conn = sqlite3.connect(DB_FILE_USER)
    conn.row_factory = sqlite3.Row # 允许通过列名访问
    c = conn.cursor()
    c.execute("SELECT * FROM shortcuts ORDER BY added_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def delete_shortcut(shortcut_id):
    """删除快捷方式"""
    conn = sqlite3.connect(DB_FILE_USER)
    c = conn.cursor()
    c.execute("DELETE FROM shortcuts WHERE id = ?", (shortcut_id,))
    conn.commit()
    conn.close()

def increment_run_count(shortcut_id):
    """增加启动次数"""
    conn = sqlite3.connect(DB_FILE_USER)
    c = conn.cursor()
    c.execute("UPDATE shortcuts SET run_count = run_count + 1 WHERE id = ?", (shortcut_id,))
    conn.commit()
    conn.close()