import sqlite3
import os
from .const import DB_FILE_USER, DB_FILE_CACHE


def _get_user_conn():
    """获取用户数据库连接，启用外键和 WAL 模式"""
    conn = sqlite3.connect(DB_FILE_USER, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


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
    c.execute('''CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    sort_order INTEGER DEFAULT 0
                )''')
    conn.commit()
    conn.close()


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


# --- CRUD 操作 ---

def add_shortcut_to_db(name, exe_path, lnk_path, source_type, args=""):
    """添加一个快捷方式到数据库（带事务保护）"""
    conn = _get_user_conn()
    try:
        c = conn.cursor()
        c.execute("SELECT id FROM shortcuts WHERE exe_path = ?", (exe_path,))
        data = c.fetchone()
        if data:
            c.execute("UPDATE shortcuts SET name=?, lnk_path=?, source_type=?, args=? WHERE id=?",
                      (name, lnk_path, source_type, args, data[0]))
        else:
            c.execute("INSERT INTO shortcuts (name, exe_path, lnk_path, source_type, args) VALUES (?, ?, ?, ?, ?)",
                      (name, exe_path, lnk_path, source_type, args))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"DB Error (add_shortcut): {e}")
        return False
    finally:
        conn.close()


def get_all_shortcuts():
    """获取所有快捷方式"""
    conn = _get_user_conn()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM shortcuts ORDER BY added_at DESC")
        return c.fetchall()
    finally:
        conn.close()


def delete_shortcut(shortcut_id):
    """删除快捷方式（带事务保护）"""
    conn = _get_user_conn()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM shortcuts WHERE id = ?", (shortcut_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"DB Error (delete): {e}")
    finally:
        conn.close()


def increment_run_count(shortcut_id):
    """增加启动次数"""
    conn = _get_user_conn()
    try:
        c = conn.cursor()
        c.execute("UPDATE shortcuts SET run_count = run_count + 1 WHERE id = ?", (shortcut_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"DB Error (increment): {e}")
    finally:
        conn.close()


def get_shortcut_stats():
    """获取数据库统计信息"""
    conn = _get_user_conn()
    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM shortcuts")
        total = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(run_count), 0) FROM shortcuts")
        total_runs = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM shortcuts WHERE run_count > 0")
        launched = c.fetchone()[0]
        c.execute("SELECT source_type, COUNT(*) FROM shortcuts GROUP BY source_type")
        by_source = dict(c.fetchall())
        return {
            'total': total,
            'total_runs': total_runs,
            'launched': launched,
            'by_source': by_source
        }
    finally:
        conn.close()


def get_top_shortcuts(limit=10):
    """获取启动次数最多的快捷方式"""
    conn = _get_user_conn()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM shortcuts WHERE run_count > 0 ORDER BY run_count DESC LIMIT ?", (limit,))
        return c.fetchall()
    finally:
        conn.close()


def get_db_size():
    """获取数据库文件大小"""
    try:
        size = os.path.getsize(DB_FILE_USER)
        for ext in ['-wal', '-shm']:
            f = DB_FILE_USER + ext
            if os.path.exists(f):
                size += os.path.getsize(f)
        # 缓存数据库
        if os.path.exists(DB_FILE_CACHE):
            size += os.path.getsize(DB_FILE_CACHE)
        return size
    except OSError:
        return 0


def clear_cache_db():
    """清空缓存数据库"""
    try:
        import sqlite3
        conn = sqlite3.connect(DB_FILE_CACHE)
        conn.execute("DELETE FROM icon_cache")
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def vacuum_databases():
    """压缩数据库，回收空间"""
    try:
        import sqlite3
        for db_path in [DB_FILE_USER, DB_FILE_CACHE]:
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.execute("VACUUM")
                conn.close()
        return True
    except Exception:
        return False
