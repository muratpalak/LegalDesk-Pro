"""SQLite storage and synthetic demonstration records.

Local-only MVP. Neither encrypted storage nor production access controls are provided.
"""
from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import date, datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("LEGALDESK_DATA_DIR", BASE_DIR / "app" / "data"))
DB_FILE = DATA_DIR / "legaldesk.sqlite3"
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS clients (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'Bireysel',
 company TEXT DEFAULT '', email TEXT DEFAULT '', phone TEXT DEFAULT '', notes TEXT DEFAULT '',
 created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS cases (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 reference TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
 client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
 court TEXT DEFAULT '', case_type TEXT DEFAULT 'Diğer',
 status TEXT NOT NULL DEFAULT 'Aktif', priority TEXT NOT NULL DEFAULT 'Normal',
 description TEXT DEFAULT '', opened_on TEXT DEFAULT '', created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
 case_id INTEGER REFERENCES cases(id) ON DELETE SET NULL,
 kind TEXT NOT NULL DEFAULT 'Duruşma', starts_at TEXT NOT NULL,
 location TEXT DEFAULT '', notes TEXT DEFAULT '', created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS tasks (
 id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
 case_id INTEGER REFERENCES cases(id) ON DELETE SET NULL,
 due_date TEXT DEFAULT '', priority TEXT NOT NULL DEFAULT 'Normal',
 done INTEGER NOT NULL DEFAULT 0 CHECK(done IN(0,1)),
 notes TEXT DEFAULT '', created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS transactions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 case_id INTEGER REFERENCES cases(id) ON DELETE SET NULL,
 client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL,
 kind TEXT NOT NULL CHECK(kind IN ('Tahsilat','Masraf')),
 amount REAL NOT NULL CHECK(amount >= 0),
 description TEXT NOT NULL, transaction_date TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS documents (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
 filename TEXT NOT NULL, storage_name TEXT NOT NULL UNIQUE,
 mime TEXT NOT NULL, size INTEGER NOT NULL,
 created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS activities (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 action TEXT NOT NULL, details TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cases_client ON cases(client_id);
CREATE INDEX IF NOT EXISTS idx_events_start ON events(starts_at);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date);
"""

@contextmanager
def connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_FILE, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('PRAGMA busy_timeout=5000')
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def log(c, action: str, details: str):
    c.execute("INSERT INTO activities(action, details) VALUES (?,?)", (action, details[:400]))

def initialize():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connection() as c:
        c.executescript(SCHEMA)
        existing = c.execute('SELECT count(*) FROM clients').fetchone()[0]
        if existing:
            return
        today = date.today()
        clients = [
            ('Ayşe Yılmaz','Bireysel','','ayse@example.com','+90 555 000 00 01','Demo kayıt — gerçek kişi verisi değildir.'),
            ('Atlas Teknoloji A.Ş.','Kurumsal','Atlas Teknoloji','info@atlas.example','+90 555 000 00 02','Demo şirket.'),
            ('Mehmet Kaya','Bireysel','','mehmet@example.com','+90 555 000 00 03','Demo kayıt.'),
            ('Nova Gayrimenkul Ltd.','Kurumsal','Nova Gayrimenkul','office@nova.example','+90 555 000 00 04','Demo şirket.'),
            ('Elif Demir','Bireysel','','elif@example.com','+90 555 000 00 05','Demo kayıt.'),
        ]
        c.executemany('INSERT INTO clients(name,kind,company,email,phone,notes) VALUES (?,?,?,?,?,?)',clients)
        cases = [
            ('2026/001','İş Sözleşmesi İncelemesi',2,'İstanbul İş Mahkemesi','İş Hukuku','Aktif','Yüksek','Örnek hukuki dosya.',today.isoformat()),
            ('2026/002','Kira Uyuşmazlığı',1,'İstanbul Sulh Hukuk Mahkemesi','Gayrimenkul','Aktif','Normal','Örnek hukuki dosya.',(today-timedelta(days=27)).isoformat()),
            ('2026/003','Ticari Alacak Takibi',4,'İstanbul Asliye Ticaret Mahkemesi','Ticaret Hukuku','Beklemede','Normal','Örnek hukuki dosya.',(today-timedelta(days=34)).isoformat()),
            ('2026/004','Sözleşme Feshi',3,'İstanbul Asliye Hukuk Mahkemesi','Borçlar Hukuku','Aktif','Yüksek','Örnek hukuki dosya.',(today-timedelta(days=60)).isoformat()),
            ('2026/005','Marka Danışmanlığı',2,'','Fikri Mülkiyet','Tamamlandı','Düşük','Örnek hukuki dosya.',(today-timedelta(days=70)).isoformat()),
            ('2026/006','Miras Paylaşımı',5,'İstanbul Sulh Hukuk Mahkemesi','Miras Hukuku','Aktif','Normal','Örnek hukuki dosya.',(today-timedelta(days=9)).isoformat()),
        ]
        c.executemany('INSERT INTO cases(reference,title,client_id,court,case_type,status,priority,description,opened_on) VALUES (?,?,?,?,?,?,?,?,?)', cases)
        events = [
            ('İş davası duruşması',1,'Duruşma',(today+timedelta(days=2)).isoformat()+'T10:30','İstanbul Adliyesi','Dosyaları kontrol et'),
            ('Müvekkil görüşmesi',2,'Görüşme',(today+timedelta(days=4)).isoformat()+'T14:00','Ofis','Örnek toplantı'),
            ('Ticari dosya kontrolü',3,'Hatırlatma',(today+timedelta(days=7)).isoformat()+'T09:15','Online',''),
            ('Miras dosyası görüşmesi',6,'Görüşme',(today+timedelta(days=11)).isoformat()+'T11:00','Ofis',''),
            ('Sözleşme feshi duruşması',4,'Duruşma',(today+timedelta(days=18)).isoformat()+'T13:45','İstanbul Adliyesi',''),
        ]
        c.executemany('INSERT INTO events(title,case_id,kind,starts_at,location,notes) VALUES (?,?,?,?,?,?)',events)
        tasks = [
            ('Sözleşme eklerini kontrol et',1,(today+timedelta(days=1)).isoformat(),'Yüksek',0,''),
            ('Kira dosyası belgelerini incele',2,(today+timedelta(days=3)).isoformat(),'Normal',0,''),
            ('Tahsilat kaydını güncelle',3,(today+timedelta(days=5)).isoformat(),'Normal',0,''),
            ('Görüşme notlarını hazırla',6,(today+timedelta(days=9)).isoformat(),'Düşük',0,''),
            ('Danışmanlık dosyasını kapat',5,(today-timedelta(days=3)).isoformat(),'Normal',1,''),
        ]
        c.executemany('INSERT INTO tasks(title,case_id,due_date,priority,done,notes) VALUES (?,?,?,?,?,?)',tasks)
        trans = [
            (1,2,'Tahsilat',12500.0,'Danışmanlık ücreti',(today-timedelta(days=13)).isoformat()),
            (2,1,'Masraf',1850.0,'Dosya gideri',(today-timedelta(days=10)).isoformat()),
            (4,3,'Tahsilat',8000.0,'Hizmet tahsilatı',(today-timedelta(days=6)).isoformat()),
            (6,5,'Masraf',550.0,'Noter masrafı',(today-timedelta(days=2)).isoformat()),
            (5,2,'Tahsilat',6200.0,'Danışmanlık tahsilatı',(today-timedelta(days=30)).isoformat()),
        ]
        c.executemany('INSERT INTO transactions(case_id,client_id,kind,amount,description,transaction_date) VALUES (?,?,?,?,?,?)',trans)
        log(c,'Başlangıç','Sentetik örnek veriler oluşturuldu')
