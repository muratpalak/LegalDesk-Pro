"""Run with: pytest -q"""
from __future__ import annotations
import base64
import pytest
from fastapi.testclient import TestClient
from app import db, main

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'DATA_DIR',tmp_path)
    monkeypatch.setattr(db,'DB_FILE',tmp_path/'legaldesk.sqlite3')
    monkeypatch.setattr(main,'UPLOAD_DIR',tmp_path/'documents')
    with TestClient(main.app) as test:
        yield test

def test_demo_seed_and_health(client):
    assert client.get('/api/health').json()['mode']=='local-demo'
    result=client.get('/api/state')
    assert result.status_code==200
    data=result.json()
    assert len(data['clients'])==5
    assert len(data['cases'])==6
    assert len(data['events'])==5
    assert len(data['tasks'])==5
    assert len(data['transactions'])==5
    assert len(data['documents'])==0
    assert result.headers['X-Frame-Options']=='DENY'

def test_client_create_edit_delete(client):
    payload={'name':'Demo Test Müvekkil','email':'test@example.com'}
    r=client.post('/api/clients',json=payload)
    assert r.status_code==201,r.text
    id=r.json()['id']
    assert r.json()['kind']=='Bireysel'
    payload['kind']='Kurumsal'
    r=client.put(f'/api/clients/{id}',json=payload)
    assert r.status_code==200 and r.json()['kind']=='Kurumsal'
    r=client.delete(f'/api/clients/{id}')
    assert r.status_code==200
    assert client.delete(f'/api/clients/{id}').status_code==404

def test_case_crud_and_unique_number(client):
    payload={'reference':'DEMO-TEST-123','title':'Örnek Test Dosyası','client_id':1,'status':'Aktif'}
    r=client.post('/api/cases',json=payload)
    assert r.status_code==201,r.text
    assert client.post('/api/cases',json=payload).status_code==409
    assert client.delete('/api/clients/1').status_code==409
    payload['status']='Tamamlandı'
    r=client.put(f"/api/cases/{r.json()['id']}",json=payload)
    assert r.json()['status']=='Tamamlandı'

def test_validation_and_no_sql_query_escape(client):
    assert client.get('/api/fake_table').status_code==404
    assert client.post('/api/clients',json={'name':'x'}).status_code==422
    assert client.post('/api/cases',json={'reference':'100', 'title':'test', 'client_id':99999}).status_code==409
    assert client.post('/api/events',json={'title':'Tarih test','starts_at':'not-a-date'}).status_code==422
    assert client.post('/api/transactions',json={'kind':'Tahsilat','amount':-1,'description':'Test','transaction_date':'2026-10-20'}).status_code==422

def test_tasks_toggle_and_finance(client):
    r=client.post('/api/tasks',json={'title':'Örnek görev','priority':'Yüksek','done':False,'case_id':1})
    assert r.status_code==201
    d=r.json()
    d['done']=True
    r=client.put(f'/api/tasks/{d["id"]}',json=d)
    assert r.status_code==200 and r.json()['done']==1
    r=client.post('/api/transactions',json={'kind':'Masraf','amount':49.5,'description':'Örnek masraf','transaction_date':'2026-10-20','case_id':1})
    assert r.status_code==201 and r.json()['amount']==49.5

def test_document_upload_download_delete(client):
    content=b'%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n%%EOF'
    payload={'case_id':1,'filename':'test.pdf','data':base64.b64encode(content).decode()}
    r=client.post('/api/documents',json=payload)
    assert r.status_code==201,r.text
    id=r.json()['id']
    r=client.get(f'/api/documents/{id}/download')
    assert r.status_code==200 and r.content==content
    assert client.delete(f'/api/cases/1').status_code==409
    assert client.delete(f'/api/documents/{id}').status_code==200
    assert client.get(f'/api/documents/{id}/download').status_code==404

def test_reject_invalid_document(client):
    bad={'case_id':1,'filename':'malware.exe','data':base64.b64encode(b'TEST').decode()}
    assert client.post('/api/documents',json=bad).status_code==400
    bad['filename']='f.pdf'
    assert client.post('/api/documents',json=bad).status_code==400

def test_csv_export(client):
    r=client.get('/api/export/cases.csv')
    assert r.status_code==200 and 'text/csv' in r.headers['content-type']
    assert 'Dosya No' in r.text and '2026/001' in r.text
