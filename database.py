# app/database.py
import sqlite3
import datetime
from typing import Dict, Any

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS usage (
            ip_address TEXT,
            user_id TEXT,
            date TEXT,
            scans_today INTEGER DEFAULT 0,
            total_scans INTEGER DEFAULT 0,
            is_premium BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (ip_address, date)
        )
    ''')
    conn.commit()
    conn.close()

def can_user_scan(ip_address: str, user_id: str = "anonymous") -> Dict[str, Any]:
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    c.execute('''
        INSERT OR IGNORE INTO usage (ip_address, user_id, date, scans_today, total_scans)
        VALUES (?, ?, ?, 0, 0)
    ''', (ip_address, user_id, today))
    
    c.execute('''
        SELECT scans_today, is_premium FROM usage 
        WHERE ip_address = ? AND date = ?
    ''', (ip_address, today))
    
    result = c.fetchone()
    conn.close()
    
    if result:
        scans_today, is_premium = result
        # Premium users have unlimited scans
        if is_premium:
            return {"can_scan": True, "reason": "premium_user", "scans_left": "unlimited"}
        # Free users: max 1 scan per day
        elif scans_today < 1:
            return {"can_scan": True, "reason": "free_scan_available", "scans_left": 1 - scans_today}
        else:
            return {"can_scan": False, "reason": "daily_limit_reached", "scans_left": 0}
    
    return {"can_scan": False, "reason": "error", "scans_left": 0}

def record_scan(ip_address: str, user_id: str = "anonymous"):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    c.execute('''
        UPDATE usage 
        SET scans_today = scans_today + 1, total_scans = total_scans + 1
        WHERE ip_address = ? AND date = ?
    ''', (ip_address, today))
    
    conn.commit()
    conn.close()