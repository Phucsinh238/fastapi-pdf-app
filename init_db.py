import sqlite3
import hashlib
import os
import sqlite3, hashlib

# Tạo thư mục database nếu chưa có
os.makedirs("app", exist_ok=True)

# Kết nối file database
conn = sqlite3.connect("app/document.db")
cur = conn.cursor()

# Tạo bảng users
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    email TEXT UNIQUE,
    password TEXT,
    active INTEGER DEFAULT 1,
    role TEXT DEFAULT 'superadmin'
)
""")

# Tạo bảng log truy cập
cur.execute("""
CREATE TABLE IF NOT EXISTS login_log (
    username TEXT,
    ip TEXT,
    user_agent TEXT,
    timestamp TEXT
)
""")

# Tạo admin mẫu
username = "admin"
email = "admin@example.com"
password = "123456"
hashed = hashlib.sha256(password.encode()).hexdigest()

cur.execute("INSERT OR IGNORE INTO users (username, email, password, active, role) VALUES (?, ?, ?, ?, ?)",
            (username, email, hashed, 1, "superadmin"))

conn.commit()
conn.close()

print("✅ Database created & sample superadmin added.")



conn = sqlite3.connect("app/document.db")
cur = conn.cursor()
new_hash = hashlib.sha256("123456".encode()).hexdigest()
cur.execute("UPDATE users SET password = ?, active = 1, role = 'superadmin' WHERE username = 'admin'", (new_hash,))
conn.commit()
conn.close()
print("✅ Admin password updated.")
