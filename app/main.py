"""LegalDesk Pro – local-only legal office demo API.

Not intended for storing real client data without a security assessment.
"""
from __future__ import annotations
import base64
import binascii
import csv
import io
import os
import re
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, ValidationError

from .db import BASE_DIR, DATA_DIR, connection, initialize, log

STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = DATA_DIR / "documents"
UPLOAD_LIMIT = 5 * 1024 * 1024
ALLOWED = {'.pdf': 'application/pdf','.png': 'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.txt':'text/plain','.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}

@asynccontextmanager
async def lifespan(app):
    initialize()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(title='LegalDesk Pro', version='1.0.0', description='Local demonstration API; synthetic records only.', lifespan=lifespan, docs_url='/api/docs', redoc_url=None)

@app.middleware('http')
async def security_headers(request:Request,call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    return response

class ClientIn(BaseModel):
    name: str = Field(min_length=2,max_length=160)
    kind: Literal['Bireysel','Kurumsal']='Bireysel'
    company: str=Field(default='',max_length=160)
    email: str=Field(default='',max_length=200)
    phone: str=Field(default='',max_length=60)
    notes: str=Field(default='',max_length=2000)

class CaseIn(BaseModel):
    reference: str=Field(min_length=2,max_length=55)
    title: str=Field(min_length=3,max_length=180)
    client_id: int=Field(gt=0)
    court: str=Field(default='',max_length=200)
    case_type: str=Field(default='Diğer',max_length=80)
    status: Literal['Aktif','Beklemede','Tamamlandı']='Aktif'
    priority: Literal['Düşük','Normal','Yüksek']='Normal'
    description: str=Field(default='',max_length=2000)
    opened_on: str=Field(default='',max_length=10)
    @field_validator('opened_on')
    @classmethod
    def valid_opened(cls,v):
        if v:
            try:date.fromisoformat(v)
            except ValueError:raise ValueError('Geçerli bir tarih girin')
        return v

class EventIn(BaseModel):
    title: str=Field(min_length=2,max_length=180)
    case_id: int|None=None
    kind: Literal['Duruşma','Görüşme','Hatırlatma']='Duruşma'
    starts_at: str=Field(min_length=16,max_length=19)
    location: str=Field(default='',max_length=160)
    notes: str=Field(default='',max_length=1200)
    @field_validator('starts_at')
    @classmethod
    def valid_date(cls,v):
        try:datetime.fromisoformat(v)
        except ValueError:raise ValueError('Geçerli bir tarih ve saat girin')
        return v

class TaskIn(BaseModel):
    title: str=Field(min_length=2,max_length=180)
    case_id: int|None=None
    due_date: str=Field(default='',max_length=10)
    priority: Literal['Düşük','Normal','Yüksek']='Normal'
    done: bool=False
    notes: str=Field(default='',max_length=1200)
    @field_validator('due_date')
    @classmethod
    def valid_due(cls,v):
        if v:
            try:date.fromisoformat(v)
            except ValueError:raise ValueError('Geçerli bir tarih girin')
        return v

class TransactionIn(BaseModel):
    case_id: int|None=None
    client_id: int|None=None
    kind: Literal['Tahsilat','Masraf']
    amount: float=Field(ge=0,le=100_000_000)
    description: str=Field(min_length=2,max_length=250)
    transaction_date: str=Field(min_length=10,max_length=10)
    @field_validator('transaction_date')
    @classmethod
    def valid_date(cls,v):
        try:date.fromisoformat(v)
        except ValueError:raise ValueError('Geçerli bir tarih girin')
        return v

class DocumentIn(BaseModel):
    case_id: int=Field(gt=0)
    filename: str=Field(min_length=1,max_length=180)
    data: str=Field(min_length=1,max_length=7_500_000)

MODELS = {'clients':ClientIn,'cases':CaseIn,'events':EventIn,'tasks':TaskIn,'transactions':TransactionIn}
SORTS = {'clients':'id DESC','cases':'id DESC','events':'starts_at ASC','tasks':'done ASC, due_date ASC','transactions':'transaction_date DESC, id DESC','documents':'id DESC'}
DISPLAY={'clients':'Müvekkil','cases':'Dosya','events':'Etkinlik','tasks':'Görev','transactions':'Finans kaydı'}

def all_rows(c, table):
    return [dict(r) for r in c.execute(f'SELECT * FROM {table} ORDER BY {SORTS[table]}').fetchall()]

def find_one(c,table,id):
    r=c.execute(f'SELECT * FROM {table} WHERE id=?',(id,)).fetchone()
    if r is None:raise HTTPException(404,'Kayıt bulunamadı')
    return dict(r)

def db_error(exc):
    msg = str(exc)
    if 'UNIQUE' in msg:raise HTTPException(409,'Bu dosya numarası daha önce kullanılmış')
    if 'FOREIGN KEY' in msg:raise HTTPException(409,'İlişkili kayıtlar bulundu veya bağlı dosya mevcut değil')
    raise HTTPException(400,'Geçersiz kayıt bilgisi')

@app.get('/api/health')
def health():
    return {'ok': True, 'mode':'local-demo', 'version':'1.0.0'}

@app.get('/api/state')
def state():
    with connection() as c:
        items={table:all_rows(c,table) for table in SORTS}
        items['activities']=[dict(r) for r in c.execute('SELECT * FROM activities ORDER BY id DESC LIMIT 12')]
    items['mode']='demo'
    return items

@app.post('/api/documents',status_code=201)
def upload_document(payload:DocumentIn):
    filename=Path(payload.filename.replace('\\','/')).name
    ext=Path(filename).suffix.lower()
    if ext not in ALLOWED:raise HTTPException(400,'Yalnızca PDF, DOCX, JPG, PNG ve TXT yüklenebilir')
    if len(payload.data)>7_500_000:raise HTTPException(413,'Dosya en fazla 5 MB olabilir')
    try:data=base64.b64decode(payload.data,validate=True)
    except (binascii.Error,ValueError):raise HTTPException(400,'Dosya verisi geçersiz')
    if not data or len(data)>UPLOAD_LIMIT:raise HTTPException(413,'Dosya 1 B–5 MB aralığında olmalıdır')
    magic_ok={'.pdf': data.startswith(b'%PDF-'),'.png':data.startswith(b'\x89PNG\r\n\x1a\n'),'.jpg':data.startswith(b'\xff\xd8\xff'),'.jpeg':data.startswith(b'\xff\xd8\xff'),'.docx':data.startswith(b'PK\x03\x04'),'.txt':b'\x00' not in data[:2048]}
    if not magic_ok[ext]:raise HTTPException(400,'Dosya içeriği uzantısıyla uyuşmuyor')
    storage_name=uuid.uuid4().hex+ext
    try:
        with connection() as c:
            find_one(c,'cases',payload.case_id)
            UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
            path=UPLOAD_DIR/storage_name
            path.write_bytes(data)
            try:
                cur=c.execute('INSERT INTO documents(case_id,filename,storage_name,mime,size) VALUES (?,?,?,?,?)',(payload.case_id,filename,storage_name,ALLOWED[ext],len(data)))
                log(c,'Belge yüklendi',f'{filename[:110]} / Dosya #{payload.case_id}')
                result=find_one(c,'documents',cur.lastrowid)
                return result
            except Exception:
                path.unlink(missing_ok=True)
                raise
    except sqlite3.IntegrityError as e:db_error(e)


@app.get('/api/{table}')
def list_records(table:str):
    if table not in SORTS: raise HTTPException(404,'Bilinmeyen bölüm')
    with connection() as c:return all_rows(c,table)

@app.post('/api/{table}', status_code=201)
def create_record(table:str, payload:dict):
    if table not in MODELS:raise HTTPException(404,'Bilinmeyen bölüm')
    try:record=MODELS[table](**payload).model_dump()
    except ValidationError as e:raise HTTPException(422,[{'loc':list(err['loc']),'msg':err['msg']} for err in e.errors()])
    columns=list(record)
    columns_sql=','.join(columns)
    slots=','.join('?' for _ in columns)
    try:
        with connection() as c:
            cur=c.execute(f'INSERT INTO {table} ({columns_sql}) VALUES ({slots})',list(record.values()))
            new_id=cur.lastrowid
            log(c,'Eklendi',f'{DISPLAY[table]} #{new_id}: {record.get("name") or record.get("title") or record.get("description")}')
            result=find_one(c,table,new_id)
            return result
    except sqlite3.IntegrityError as e:db_error(e)

@app.put('/api/{table}/{id}')
def update_record(table:str,id:int,payload:dict):
    if table not in MODELS:raise HTTPException(404,'Bilinmeyen bölüm')
    try:record=MODELS[table](**payload).model_dump()
    except ValidationError as e:raise HTTPException(422,[{'loc':list(err['loc']),'msg':err['msg']} for err in e.errors()])
    try:
        with connection() as c:
            find_one(c,table,id)
            setters=','.join(f'{field}=?' for field in record)
            c.execute(f'UPDATE {table} SET {setters} WHERE id=?',list(record.values())+[id])
            log(c,'Güncellendi',f'{DISPLAY[table]} #{id}')
            return find_one(c,table,id)
    except sqlite3.IntegrityError as e:db_error(e)

@app.delete('/api/{table}/{id}')
def delete_record(table:str,id:int):
    if table not in MODELS and table!='documents':raise HTTPException(404,'Bilinmeyen bölüm')
    try:
        with connection() as c:
            row=find_one(c,table,id)
            if table=='documents':
                path=UPLOAD_DIR/row['storage_name']
                c.execute('DELETE FROM documents WHERE id=?',(id,))
                if path.exists(): path.unlink()
            else:c.execute(f'DELETE FROM {table} WHERE id=?',(id,))
            log(c,'Silindi',f'{DISPLAY.get(table,"Belge")} #{id}')
            return {'deleted':id}
    except sqlite3.IntegrityError as e:db_error(e)

@app.get('/api/documents/{id}/download')
def download_document(id:int):
    with connection() as c:row=find_one(c,'documents',id)
    path=UPLOAD_DIR/row['storage_name']
    if not path.is_file():raise HTTPException(404,'Belge dosyası bulunamadı')
    return FileResponse(path,media_type='application/octet-stream',filename=row['filename'],content_disposition_type='attachment')

@app.get('/api/export/cases.csv')
def export_cases():
    with connection() as c:
        rows=[dict(r) for r in c.execute('''SELECT cases.reference, cases.title, clients.name AS client, cases.court, cases.case_type, cases.status, cases.priority, cases.opened_on FROM cases JOIN clients ON clients.id=cases.client_id ORDER BY cases.id DESC''')]
    output=io.StringIO()
    writer=csv.writer(output)
    writer.writerow(['Dosya No','Başlık','Müvekkil','Mahkeme','Tür','Durum','Öncelik','Açılış'])
    for row in rows:
        # Mitigate CSV formula injection when opened in spreadsheet apps.
        writer.writerow(["'"+str(v) if str(v).startswith(('=','+','-','@','\t','\r')) else v for v in row.values()])
    return Response('\ufeff'+output.getvalue(),media_type='text/csv; charset=utf-8', headers={'Content-Disposition':'attachment; filename="legaldesk-dosyalar.csv"'})

app.mount('/static', StaticFiles(directory=STATIC_DIR),name='static')

@app.get('/',response_class=HTMLResponse)
def index():
    return (STATIC_DIR/'index.html').read_text(encoding='utf-8')
