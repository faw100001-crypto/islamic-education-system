#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مساعد قاعدة البيانات - يدعم SQLite و PostgreSQL
"""

import os
import sqlite3

def get_db_connection():
    """إنشاء اتصال قاعدة البيانات حسب البيئة"""
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            # Fix for Railway/Heroku DATABASE_URL format
            if DATABASE_URL.startswith('postgres://'):
                DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
            
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            return conn
        except ImportError:
            print("⚠️  psycopg2 not installed, falling back to SQLite")
            conn = sqlite3.connect('islamic_education.db')
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            print(f"PostgreSQL connection failed: {e}, falling back to SQLite")
            conn = sqlite3.connect('islamic_education.db')
            conn.row_factory = sqlite3.Row
            return conn
    else:
        conn = sqlite3.connect('islamic_education.db')
        # تمكين الوصول للأعمدة بالاسم
        conn.row_factory = sqlite3.Row
        return conn

def init_database():
    """تهيئة قاعدة البيانات حسب البيئة"""
    DATABASE_URL = os.environ.get('DATABASE_URL')
    USE_POSTGRES = DATABASE_URL is not None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            # PostgreSQL Tables
            
            # جدول المعلمين
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS teachers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    gender VARCHAR(20) NOT NULL,
                    phone VARCHAR(20),
                    email VARCHAR(255),
                    qualification TEXT,
                    specialization TEXT,
                    experience_years INTEGER DEFAULT 0,
                    salary DECIMAL(10,2),
                    status VARCHAR(20) DEFAULT 'نشط',
                    hire_date DATE,
                    notes TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول الحلقات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS halaqat (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    teacher_id INTEGER,
                    teacher_name VARCHAR(255) NOT NULL,
                    location VARCHAR(255) NOT NULL,
                    max_capacity INTEGER DEFAULT 30,
                    schedule_days TEXT,
                    start_time TIME,
                    end_time TIME,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE SET NULL
                )
            ''')
            
            # جدول الطلاب
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS students (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    age INTEGER NOT NULL,
                    gender VARCHAR(20) NOT NULL,
                    phone VARCHAR(20),
                    guardian_name VARCHAR(255) NOT NULL,
                    guardian_phone VARCHAR(20) NOT NULL,
                    halaqa_id INTEGER,
                    memorization_level VARCHAR(100),
                    enrollment_date DATE DEFAULT CURRENT_DATE,
                    status VARCHAR(20) DEFAULT 'نشط',
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (halaqa_id) REFERENCES halaqat(id) ON DELETE SET NULL
                )
            ''')
            
            # جدول الحضور
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id SERIAL PRIMARY KEY,
                    student_id INTEGER NOT NULL,
                    halaqa_id INTEGER NOT NULL,
                    attendance_date DATE NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    memorization_progress TEXT,
                    performance VARCHAR(20),
                    notes TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                    FOREIGN KEY (halaqa_id) REFERENCES halaqat(id) ON DELETE CASCADE,
                    UNIQUE(student_id, attendance_date)
                )
            ''')
            
            # جدول التبرعات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS donations (
                    id SERIAL PRIMARY KEY,
                    donor_name VARCHAR(255) NOT NULL,
                    donor_phone VARCHAR(20),
                    donor_email VARCHAR(255),
                    amount DECIMAL(10,2) NOT NULL,
                    donation_date DATE NOT NULL,
                    allocation VARCHAR(100),
                    halaqa_id INTEGER,
                    notes TEXT,
                    status VARCHAR(20) DEFAULT 'مكتمل',
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (halaqa_id) REFERENCES halaqat(id) ON DELETE SET NULL
                )
            ''')
            
            # جدول حملات جمع التبرعات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fundraising_campaigns (
                    id SERIAL PRIMARY KEY,
                    campaign_name VARCHAR(255) NOT NULL,
                    platform VARCHAR(100) NOT NULL,
                    target_amount DECIMAL(10,2) NOT NULL,
                    current_amount DECIMAL(10,2) DEFAULT 0,
                    target_audience TEXT,
                    campaign_description TEXT,
                    campaign_hashtags TEXT,
                    start_date DATE,
                    end_date DATE,
                    status VARCHAR(20) DEFAULT 'مخطط',
                    ai_suggestions TEXT,
                    best_posting_times TEXT,
                    created_by VARCHAR(100) DEFAULT 'النظام',
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
        else:
            # SQLite Tables (للتشغيل المحلي)
            
            # جدول المعلمين
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS teachers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    gender TEXT NOT NULL,
                    phone TEXT,
                    email TEXT,
                    qualification TEXT,
                    specialization TEXT,
                    experience_years INTEGER DEFAULT 0,
                    salary DECIMAL(10,2),
                    status TEXT DEFAULT 'نشط',
                    hire_date DATE,
                    notes TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول الحلقات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS halaqat (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    teacher_id INTEGER,
                    teacher_name TEXT NOT NULL,
                    location TEXT NOT NULL,
                    max_capacity INTEGER DEFAULT 30,
                    schedule_days TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (teacher_id) REFERENCES teachers (id)
                )
            ''')
            
            # جدول الطلاب
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    gender TEXT NOT NULL,
                    phone TEXT,
                    guardian_name TEXT NOT NULL,
                    guardian_phone TEXT NOT NULL,
                    halaqa_id INTEGER,
                    memorization_level TEXT,
                    enrollment_date DATE DEFAULT CURRENT_DATE,
                    status TEXT DEFAULT 'نشط',
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (halaqa_id) REFERENCES halaqat (id)
                )
            ''')
            
            # جدول الحضور
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    halaqa_id INTEGER NOT NULL,
                    attendance_date DATE NOT NULL,
                    status TEXT NOT NULL,
                    memorization_progress TEXT,
                    performance TEXT,
                    notes TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students (id),
                    FOREIGN KEY (halaqa_id) REFERENCES halaqat (id),
                    UNIQUE(student_id, attendance_date)
                )
            ''')
            
            # جدول التبرعات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS donations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    donor_name TEXT NOT NULL,
                    donor_phone TEXT,
                    donor_email TEXT,
                    amount DECIMAL(10,2) NOT NULL,
                    donation_date DATE NOT NULL,
                    allocation TEXT,
                    halaqa_id INTEGER,
                    notes TEXT,
                    status TEXT DEFAULT 'مكتمل',
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (halaqa_id) REFERENCES halaqat (id)
                )
            ''')
            
            # جدول حملات جمع التبرعات
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fundraising_campaigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_name TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    target_amount DECIMAL(10,2) NOT NULL,
                    current_amount DECIMAL(10,2) DEFAULT 0,
                    target_audience TEXT,
                    campaign_description TEXT,
                    campaign_hashtags TEXT,
                    start_date DATE,
                    end_date DATE,
                    status TEXT DEFAULT 'مخطط',
                    ai_suggestions TEXT,
                    best_posting_times TEXT,
                    created_by TEXT DEFAULT 'النظام',
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        
        conn.commit()
        print(f"✅ تم إنشاء قاعدة البيانات بنجاح ({'PostgreSQL' if USE_POSTGRES else 'SQLite'})")
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء قاعدة البيانات: {e}")
        
    finally:
        conn.close()

if __name__ == '__main__':
    init_database()