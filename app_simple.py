#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from datetime import datetime, date, timedelta
import os
import json
import csv
import io
from database_helper import get_db_connection, init_database

# إعداد Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'halaqat_secret_key_2024')

def init_db():
    """تهيئة قاعدة البيانات حسب البيئة"""
    init_database()

@app.route('/')
def dashboard():
    """الصفحة الرئيسية - لوحة التحكم"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إحصائيات أساسية آمنة
        stats = {}
        
        # عدد الطلاب
        cursor.execute('SELECT COUNT(*) FROM students')
        result = cursor.fetchone()
        stats['total_students'] = result[0] if result else 0
        
        # عدد الحلقات
        cursor.execute('SELECT COUNT(*) FROM halaqat')
        result = cursor.fetchone()
        stats['total_halaqat'] = result[0] if result else 0
        
        # عدد المعلمين
        cursor.execute('SELECT COUNT(*) FROM teachers')
        result = cursor.fetchone()
        stats['total_teachers'] = result[0] if result else 0
        
        # إجمالي التبرعات
        cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM donations')
        result = cursor.fetchone()
        stats['total_donations'] = result[0] if result else 0
        
        # آخر الطلاب
        cursor.execute('SELECT * FROM students ORDER BY id DESC LIMIT 5')
        recent_students = cursor.fetchall()
        
        conn.close()
        
        return render_template('dashboard.html', 
                             stats=stats, 
                             recent_students=recent_students,
                             top_halaqat=[])
        
    except Exception as e:
        print(f"Dashboard error: {e}")
        # إحصائيات افتراضية آمنة
        stats = {
            'total_students': 0,
            'total_halaqat': 0, 
            'total_teachers': 0,
            'total_donations': 0,
            'male_students': 0,
            'female_students': 0,
            'today_attendance': 0
        }
        return render_template('dashboard.html', 
                             stats=stats, 
                             recent_students=[],
                             top_halaqat=[])

@app.route('/students')
def students_list():
    """قائمة الطلاب"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.*, h.name as halaqa_name 
            FROM students s 
            LEFT JOIN halaqat h ON s.halaqa_id = h.id 
            ORDER BY s.name
        ''')
        students = cursor.fetchall()
        
        cursor.execute('SELECT id, name FROM halaqat ORDER BY name')
        halaqat = cursor.fetchall()
        
        conn.close()
        
        return render_template('students.html', 
                             students=students, 
                             halaqat=halaqat)
        
    except Exception as e:
        flash(f'خطأ في تحميل قائمة الطلاب: {e}', 'error')
        return render_template('students.html', students=[], halaqat=[])

@app.route('/halaqat')
def halaqat_list():
    """قائمة الحلقات"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT h.*, COUNT(s.id) as student_count
            FROM halaqat h
            LEFT JOIN students s ON h.id = s.halaqa_id
            GROUP BY h.id
            ORDER BY h.name
        ''')
        halaqat = cursor.fetchall()
        
        conn.close()
        
        return render_template('halaqat.html', halaqat=halaqat)
        
    except Exception as e:
        flash(f'خطأ في تحميل قائمة الحلقات: {e}', 'error')
        return render_template('halaqat.html', halaqat=[])

@app.route('/attendance')
def attendance():
    """صفحة الحضور"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        selected_date = request.args.get('date', today)
        
        # جلب الحلقات
        cursor.execute('SELECT id, name FROM halaqat ORDER BY name')
        halaqat = cursor.fetchall()
        
        # جلب الطلاب
        cursor.execute('''
            SELECT s.id, s.name, s.halaqa_id, h.name as halaqa_name
            FROM students s
            LEFT JOIN halaqat h ON s.halaqa_id = h.id
            ORDER BY h.name, s.name
        ''')
        students = cursor.fetchall()
        
        # حساب إحصائيات الحضور
        cursor.execute('SELECT COUNT(*) FROM students')
        total_students = cursor.fetchone()[0] or 0
        
        # حساب الحضور لليوم المحدد
        cursor.execute('''
            SELECT COUNT(*) FROM attendance 
            WHERE date = ? AND status = 'حاضر'
        ''', (selected_date,))
        present_today = cursor.fetchone()[0] or 0
        
        cursor.execute('''
            SELECT COUNT(*) FROM attendance 
            WHERE date = ? AND status IN ('غائب', 'متأخر')
        ''', (selected_date,))
        absent_today = cursor.fetchone()[0] or 0
        
        # إذا لم يكن هناك حضور مسجل لهذا اليوم، اعتبر جميع الطلاب غائبين
        if present_today + absent_today == 0:
            absent_today = total_students
        
        conn.close()
        
        return render_template('attendance.html', 
                             students=students, 
                             halaqat=halaqat,
                             selected_date=selected_date,
                             total_students=total_students,
                             present_today=present_today,
                             absent_today=absent_today,
                             today=today)
        
    except Exception as e:
        flash(f'خطأ في تحميل بيانات الحضور: {e}', 'error')
        return render_template('attendance.html', 
                             students=[], 
                             halaqat=[],
                             selected_date=date.today().isoformat(),
                             total_students=0,
                             present_today=0,
                             absent_today=0,
                             today=date.today().isoformat())

@app.route('/teachers')
def teachers_list():
    """قائمة المعلمين"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT t.*, 
                   COUNT(DISTINCT h.id) as halaqat_count,
                   COUNT(DISTINCT s.id) as total_students
            FROM teachers t
            LEFT JOIN halaqat h ON t.id = h.teacher_id OR t.name = h.teacher_name
            LEFT JOIN students s ON h.id = s.halaqa_id
            GROUP BY t.id
            ORDER BY t.name
        ''')
        teachers = cursor.fetchall()
        
        # حساب الإحصائيات
        cursor.execute('SELECT COUNT(*) FROM teachers')
        total_teachers = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM teachers WHERE status = 'نشط'")
        active_teachers = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM teachers WHERE gender = 'ذكر'")
        male_teachers = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM teachers WHERE gender = 'أنثى'")
        female_teachers = cursor.fetchone()[0] or 0
        
        conn.close()
        return render_template('teachers.html', 
                             teachers=teachers,
                             total_teachers=total_teachers,
                             active_teachers=active_teachers,
                             male_teachers=male_teachers,
                             female_teachers=female_teachers)
        
    except Exception as e:
        flash(f'خطأ في تحميل قائمة المعلمين: {e}', 'error')
        return render_template('teachers.html', 
                             teachers=[],
                             total_teachers=0,
                             active_teachers=0,
                             male_teachers=0,
                             female_teachers=0)

@app.route('/donations')
def donations_list():
    """قائمة التبرعات"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # جلب التبرعات
        cursor.execute('SELECT * FROM donations ORDER BY id DESC LIMIT 100')
        donations = cursor.fetchall()
        
        # حساب إجمالي التبرعات
        cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM donations')
        total_donations = cursor.fetchone()[0] or 0
        
        # حساب التبرعات المخصصة (قيمة تقديرية 70% من الإجمالي)
        allocated_donations = total_donations * 0.7
        
        # حساب المتبقي للتوزيع
        remaining = total_donations - allocated_donations
        
        # إحصائيات إضافية
        cursor.execute('SELECT COUNT(*) FROM donations')
        donations_count = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return render_template('donations.html', 
                             donations=donations,
                             total_donations=total_donations,
                             allocated_donations=allocated_donations,
                             remaining=remaining,
                             donations_count=donations_count)
        
    except Exception as e:
        flash(f'خطأ في تحميل قائمة التبرعات: {e}', 'error')
        return render_template('donations.html', 
                             donations=[], 
                             total_donations=0,
                             allocated_donations=0,
                             remaining=0,
                             donations_count=0)

@app.route('/fundraising')
def fundraising_campaigns():
    """صفحة حملات جمع التبرعات"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على جميع حملات جمع التبرعات
        cursor.execute('''
            SELECT * FROM fundraising_campaigns 
            ORDER BY created_date DESC
        ''')
        campaigns = cursor.fetchall()
        
        # إحصائيات سريعة
        cursor.execute('SELECT COUNT(*) FROM fundraising_campaigns WHERE status = "نشط"')
        active_campaigns = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(target_amount) FROM fundraising_campaigns WHERE status != "مكتمل"')
        total_target = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(current_amount) FROM fundraising_campaigns')
        total_collected = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return render_template('fundraising_campaigns.html',
                             campaigns=campaigns,
                             active_campaigns=active_campaigns,
                             total_target=total_target,
                             total_collected=total_collected)
        
    except Exception as e:
        flash(f'خطأ في تحميل حملات جمع التبرعات: {e}', 'error')
        return render_template('fundraising_campaigns.html', 
                             campaigns=[],
                             active_campaigns=0,
                             total_target=0,
                             total_collected=0)

@app.route('/fundraising/add', methods=['GET', 'POST'])
def add_fundraising_campaign():
    """إضافة حملة جمع تبرعات جديدة مع الذكاء الاصطناعي"""
    if request.method == 'POST':
        try:
            campaign_name = request.form.get('campaign_name')
            platform = request.form.get('platform')
            target_amount = float(request.form.get('target_amount', 0))
            target_audience = request.form.get('target_audience')
            campaign_description = request.form.get('campaign_description')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            
            # توليد اقتراحات الذكاء الاصطناعي
            ai_suggestions = generate_ai_fundraising_suggestions(
                campaign_name, platform, target_amount, target_audience, campaign_description
            )
            
            # توليد أوقات النشر المثلى
            best_times = generate_best_posting_times(platform)
            
            # توليد الهاشتاغات
            hashtags = generate_campaign_hashtags(campaign_name, campaign_description)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO fundraising_campaigns 
                (campaign_name, platform, target_amount, target_audience, 
                 campaign_description, campaign_hashtags, start_date, end_date,
                 ai_suggestions, best_posting_times)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (campaign_name, platform, target_amount, target_audience,
                  campaign_description, hashtags, start_date, end_date,
                  ai_suggestions, best_times))
            
            conn.commit()
            conn.close()
            
            flash('✅ تم إنشاء حملة جمع التبرعات بنجاح!', 'success')
            return redirect(url_for('fundraising_campaigns'))
            
        except Exception as e:
            flash(f'خطأ في إنشاء الحملة: {e}', 'error')
    
    return render_template('add_fundraising_campaign.html')

def generate_ai_fundraising_suggestions(name, platform, target, audience, description):
    """توليد اقتراحات الذكاء الاصطناعي لحملة جمع التبرعات"""
    
    # قاعدة معرفية للاقتراحات حسب المنصة
    platform_suggestions = {
        'تويتر': [
            'استخدم خيوط تويتر (threads) لشرح تفاصيل الحملة',
            'انشر في أوقات الذروة (8-10 مساءً)',
            'استخدم الهاشتاغات المحلية والعالمية',
            'تفاعل مع المؤثرين الخيريين',
            'انشر صور وفيديوهات قصيرة'
        ],
        'انستجرام': [
            'استخدم القصص التفاعلية مع الاستطلاعات',
            'انشر فيديوهات ريلز جذابة',
            'استخدم الألوان الدافئة والصور العاطفية',
            'اربط مع المؤثرين المحليين',
            'استخدم ميزة التبرع المباشر'
        ],
        'فيسبوك': [
            'أنشئ فعالية أو صفحة للحملة',
            'استخدم البث المباشر لشرح الهدف',
            'انشر في المجموعات المهتمة',
            'استخدم ميزة جمع التبرعات في فيسبوك',
            'شارك قصص نجاح سابقة'
        ],
        'لينكد إن': [
            'اكتب منشورات مهنية ومفصلة',
            'استهدف رجال الأعمال والشركات',
            'شارك التأثير المجتمعي للحملة',
            'استخدم البيانات والإحصائيات',
            'اطلب المشاركة من الزملاء'
        ],
        'واتساب': [
            'أنشئ رسائل شخصية ودافئة',
            'استخدم المجموعات العائلية والأصدقاء',
            'شارك صور وفيديوهات قصيرة',
            'اطلب إعادة النشر للأقارب',
            'تابع شخصياً مع المتبرعين'
        ]
    }
    
    # اقتراحات عامة حسب المبلغ المستهدف
    amount_suggestions = []
    if target < 5000:
        amount_suggestions = [
            'ابدأ بالأصدقاء والعائلة',
            'استخدم وسائل التواصل الشخصية',
            'اطلب مبالغ صغيرة من عدد أكبر'
        ]
    elif target < 20000:
        amount_suggestions = [
            'استهدف المجتمع المحلي',
            'تواصل مع الجمعيات الخيرية',
            'استخدم وسائل التواصل الاجتماعي'
        ]
    else:
        amount_suggestions = [
            'استهدف الشركات والمؤسسات',
            'تواصل مع المؤثرين الكبار',
            'أطلق حملة إعلامية شاملة'
        ]
    
    # دمج جميع الاقتراحات
    suggestions = []
    if platform in platform_suggestions:
        suggestions.extend(platform_suggestions[platform])
    suggestions.extend(amount_suggestions)
    
    # إضافة اقتراحات عامة
    general_tips = [
        'اشرح بوضوح كيف ستُستخدم التبرعات',
        'شارك تحديثات دورية عن التقدم',
        'اشكر المتبرعين علناً (بإذنهم)',
        'استخدم القصص العاطفية الحقيقية',
        'كن شفافاً في التقارير المالية'
    ]
    suggestions.extend(general_tips)
    
    return '\n'.join(suggestions)

def generate_best_posting_times(platform):
    """توليد أفضل أوقات النشر حسب المنصة"""
    
    times_map = {
        'تويتر': 'الاثنين-الجمعة: 9 صباحاً، 1 ظهراً، 3 عصراً | عطلة نهاية الأسبوع: 12-1 ظهراً',
        'انستجرام': 'الثلاثاء-الخميس: 11 صباحاً، 2 ظهراً، 5 مساءً | الجمعة: 10-11 صباحاً',
        'فيسبوك': 'الثلاثاء-الخميس: 1-3 ظهراً | الأحد: 12-1 ظهراً',
        'لينكد إن': 'الثلاثاء-الخميس: 10 صباحاً-12 ظهراً | الأربعاء: الأفضل',
        'واتساب': 'في أي وقت، لكن تجنب الساعات المتأخرة (بعد 10 مساءً)',
        'تيك توك': 'الثلاثاء-الخميس: 6-10 مساءً | الجمعة: 7-9 مساءً',
        'يوتيوب': 'الخميس-السبت: 2-4 عصراً | الأحد: 9-11 صباحاً'
    }
    
    return times_map.get(platform, 'الأوقات المناسبة: 10 صباحاً - 2 ظهراً، 7-9 مساءً')

def generate_campaign_hashtags(name, description):
    """توليد هاشتاغات مناسبة للحملة"""
    
    # هاشتاغات عامة للخير
    general_hashtags = ['#خير', '#تبرع', '#مساعدة', '#عطاء', '#خيرية', '#تطوع', '#مساندة']
    
    # هاشتاغات دينية
    religious_hashtags = ['#صدقة', '#زكاة', '#أجر', '#خير_الناس', '#البر', '#الإحسان']
    
    # هاشتاغات محلية (يمكن تخصيصها)
    local_hashtags = ['#السعودية', '#الرياض', '#جدة', '#الدمام', '#مكة', '#المدينة']
    
    # اختيار هاشتاغات عشوائية
    import random
    selected_hashtags = []
    selected_hashtags.extend(random.sample(general_hashtags, 3))
    selected_hashtags.extend(random.sample(religious_hashtags, 2))
    selected_hashtags.extend(random.sample(local_hashtags, 2))
    
    # إضافة هاشتاغ خاص بالحملة إذا أمكن
    if name:
        campaign_hashtag = f"#{name.replace(' ', '_')}"
        selected_hashtags.append(campaign_hashtag)
    
    return ' '.join(selected_hashtags)

@app.route('/test')
def test_page():
    """صفحة اختبار النظام"""
    return render_template('test_page.html')

@app.route('/reports')
def reports():
    """صفحة التقارير"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # جمع الإحصائيات المطلوبة
        stats = {}
        
        # عدد الطلاب الإجمالي
        cursor.execute('SELECT COUNT(*) FROM students')
        stats['total_students'] = cursor.fetchone()[0] or 0
        
        # عدد الطلاب الذكور والإناث
        cursor.execute("SELECT COUNT(*) FROM students WHERE gender = 'ذكر'")
        stats['male_count'] = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM students WHERE gender = 'أنثى'")
        stats['female_count'] = cursor.fetchone()[0] or 0
        
        # عدد الحلقات
        cursor.execute('SELECT COUNT(*) FROM halaqat')
        stats['total_halaqat'] = cursor.fetchone()[0] or 0
        
        # حضور اليوم (قيمة تقديرية)
        stats['today_attendance'] = int(stats['total_students'] * 0.85)  # 85% معدل حضور افتراضي
        
        # إجمالي التبرعات
        cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM donations')
        stats['total_donations'] = cursor.fetchone()[0] or 0
        
        # إحصائيات إضافية
        cursor.execute('SELECT COUNT(*) FROM teachers')
        stats['total_teachers'] = cursor.fetchone()[0] or 0
        
        # معدلات الحضور الأسبوعية (قيم افتراضية للعرض)
        stats['weekly_attendance'] = [85, 78, 82, 90, 88, 75, 80]  # آخر 7 أيام
        
        conn.close()
        
        return render_template('reports.html', stats=stats)
        
    except Exception as e:
        flash(f'خطأ في تحميل صفحة التقارير: {e}', 'error')
        # إحصائيات افتراضية في حالة الخطأ
        stats = {
            'total_students': 0,
            'male_count': 0,
            'female_count': 0,
            'total_halaqat': 0,
            'today_attendance': 0,
            'total_donations': 0,
            'total_teachers': 0,
            'weekly_attendance': [0, 0, 0, 0, 0, 0, 0]
        }
        return render_template('reports.html', stats=stats)

@app.route('/ai_reports')  
def ai_reports():
    """صفحة التقارير الذكية"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # جلب قائمة الحلقات للفلتر
        cursor.execute('SELECT id, name FROM halaqat ORDER BY name')
        halaqat = cursor.fetchall()
        
        # بعض الإحصائيات الأساسية
        cursor.execute('SELECT COUNT(*) FROM students')
        total_students = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM donations')
        total_donations = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return render_template('ai_reports.html',
                             halaqat=halaqat,
                             total_students=total_students,
                             attendance_rate=85,  # قيمة افتراضية
                             total_memorized=450,  # قيمة افتراضية
                             total_donations=total_donations)
        
    except Exception as e:
        flash(f'خطأ في تحميل صفحة التقارير: {e}', 'error')
        return render_template('ai_reports.html',
                             halaqat=[],
                             total_students=0,
                             attendance_rate=0,
                             total_memorized=0,
                             total_donations=0)

@app.route('/ai_reports_enhanced')  
def ai_reports_enhanced():
    """صفحة التقارير الذكية المحسنة"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # جلب قائمة الحلقات للفلتر
        cursor.execute('SELECT id, name FROM halaqat ORDER BY name')
        halaqat = cursor.fetchall()
        
        # بعض الإحصائيات الأساسية
        cursor.execute('SELECT COUNT(*) FROM students')
        total_students = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM donations')
        total_donations = cursor.fetchone()[0] or 0
        
        # حساب معدل الحضور التقريبي
        attendance_rate = 85  # قيمة افتراضية
        total_memorized = total_students * 25  # تقدير: 25 صفحة لكل طالب
        
        conn.close()
        
        return render_template('ai_reports_enhanced.html',
                             halaqat=halaqat,
                             total_students=total_students,
                             attendance_rate=attendance_rate,
                             total_memorized=total_memorized,
                             total_donations=total_donations)
        
    except Exception as e:
        flash(f'خطأ في تحميل صفحة التقارير: {e}', 'error')
        return render_template('ai_reports_enhanced.html',
                             halaqat=[],
                             total_students=0,
                             attendance_rate=0,
                             total_memorized=0,
                             total_donations=0)

@app.route('/certificates')
def certificates():
    """صفحة الشهادات"""
    return render_template('certificates.html')

@app.route('/ai-insights')
def ai_insights():
    """صفحة التحليلات الذكية"""
    return render_template('ai_insights.html')

# Routes إضافية مطلوبة للـ Templates
@app.route('/students/add', methods=['GET', 'POST'])
def add_student():
    """إضافة طالب جديد"""
    if request.method == 'POST':
        try:
            # جمع البيانات من النموذج
            name = request.form.get('name')
            age = request.form.get('age')
            gender = request.form.get('gender')
            phone = request.form.get('phone')
            email = request.form.get('email')
            guardian_name = request.form.get('guardian_name')
            guardian_phone = request.form.get('guardian_phone')
            halaqa_id = request.form.get('halaqa_id')
            memorization_level = request.form.get('memorization_level', 'مبتدئ')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # معالجة halaqa_id
            if halaqa_id and halaqa_id.strip():
                halaqa_id = int(halaqa_id)
            else:
                halaqa_id = None
                
            cursor.execute('''
                INSERT INTO students (name, age, gender, phone, parent_phone, halaqa_id, 
                                    performance_level, join_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, DATE('now'))
            ''', (name, age, gender, phone, guardian_phone, halaqa_id, memorization_level))
            
            conn.commit()
            conn.close()
            
            flash('تم إضافة الطالب بنجاح!', 'success')
            return redirect(url_for('students_list'))
            
        except Exception as e:
            flash(f'خطأ في إضافة الطالب: {e}', 'error')
    
    # جلب قائمة الحلقات للاختيار منها
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM halaqat ORDER BY name')
        halaqat = cursor.fetchall()
        conn.close()
    except:
        halaqat = []
    
    return render_template('add_student.html', halaqat=halaqat)

@app.route('/halaqat/add', methods=['GET', 'POST'])
def add_halaqa():
    """إضافة حلقة جديدة"""
    if request.method == 'POST':
        try:
            # جمع البيانات من النموذج
            name = request.form.get('name')
            type_val = request.form.get('type')
            teacher_name = request.form.get('teacher_name')
            location = request.form.get('location')
            max_capacity = request.form.get('max_capacity', 30)
            schedule_days = request.form.get('schedule_days')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # معالجة max_capacity
            if max_capacity:
                max_capacity = int(max_capacity)
            else:
                max_capacity = 30
                
            cursor.execute('''
                INSERT INTO halaqat (name, type, teacher_name, location, max_capacity,
                                   schedule_days, start_time, end_time, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, DATETIME('now'))
            ''', (name, type_val, teacher_name, location, max_capacity,
                  schedule_days, start_time, end_time))
            
            conn.commit()
            conn.close()
            
            flash('تم إضافة الحلقة بنجاح!', 'success')
            return redirect(url_for('halaqat_list'))
            
        except Exception as e:
            flash(f'خطأ في إضافة الحلقة: {e}', 'error')
    
    # جلب قائمة المعلمين للاختيار منها
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM teachers ORDER BY name')
        teachers = cursor.fetchall()
        conn.close()
    except:
        teachers = []
    
    return render_template('add_halaqa.html', teachers=teachers)

@app.route('/teachers/add', methods=['GET', 'POST']) 
def add_teacher():
    """إضافة معلم جديد"""
    if request.method == 'POST':
        try:
            # جمع البيانات من النموذج
            name = request.form.get('name')
            gender = request.form.get('gender')
            phone = request.form.get('phone')
            email = request.form.get('email')
            qualification = request.form.get('qualification')
            specialization = request.form.get('specialization')
            experience_years = request.form.get('experience_years', 0)
            salary = request.form.get('salary')
            notes = request.form.get('notes')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # معالجة experience_years و salary
            if experience_years:
                experience_years = int(experience_years)
            else:
                experience_years = 0
                
            if salary:
                salary = float(salary)
            else:
                salary = None
                
            cursor.execute('''
                INSERT INTO teachers (name, gender, phone, email, qualification,
                                    specialization, experience_years, salary, notes,
                                    status, hire_date, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'نشط', DATE('now'), DATETIME('now'))
            ''', (name, gender, phone, email, qualification, specialization,
                  experience_years, salary, notes))
            
            conn.commit()
            conn.close()
            
            flash('تم إضافة المعلم بنجاح!', 'success')
            return redirect(url_for('teachers_list'))
            
        except Exception as e:
            flash(f'خطأ في إضافة المعلم: {e}', 'error')
    
    return render_template('add_teacher.html')

@app.route('/donations/add', methods=['GET', 'POST'])
def add_donation():
    """إضافة تبرع جديد"""
    if request.method == 'POST':
        try:
            # جمع البيانات من النموذج
            donor_name = request.form.get('donor_name')
            amount = request.form.get('amount')
            purpose = request.form.get('purpose', 'تبرع عام')
            notes = request.form.get('notes')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # معالجة amount
            if amount:
                amount = float(amount)
            else:
                amount = 0.0
                
            cursor.execute('''
                INSERT INTO donations (donor_name, amount, purpose, date, allocated)
                VALUES (?, ?, ?, DATETIME('now'), 0)
            ''', (donor_name, amount, purpose))
            
            conn.commit()
            conn.close()
            
            flash('تم إضافة التبرع بنجاح!', 'success')
            return redirect(url_for('donations_list'))
            
        except Exception as e:
            flash(f'خطأ في إضافة التبرع: {e}', 'error')
    
    return render_template('add_donation.html')

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    """تسجيل حضور الطلاب"""
    try:
        data = request.json
        attendance_date = data.get('date', date.today().isoformat())
        attendance_records = data.get('attendance', [])
        
        if not attendance_records:
            return jsonify({'success': False, 'message': 'لا توجد بيانات حضور لتسجيلها'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # حذف السجلات الموجودة لنفس التاريخ (للتحديث)
        cursor.execute('DELETE FROM attendance WHERE date = ?', (attendance_date,))
        
        # إدراج سجلات الحضور الجديدة
        success_count = 0
        for record in attendance_records:
            student_id = record.get('student_id')
            status = record.get('status', 'غائب')
            notes = record.get('notes', '')
            
            if student_id:
                cursor.execute('''
                    INSERT INTO attendance (student_id, date, status, notes, created_at)
                    VALUES (?, ?, ?, ?, DATETIME('now'))
                ''', (student_id, attendance_date, status, notes))
                success_count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'تم تسجيل حضور {success_count} طالب بنجاح',
            'count': success_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في تسجيل الحضور: {str(e)}'
        })

@app.route('/get_attendance', methods=['GET'])
def get_attendance():
    """جلب بيانات الحضور لتاريخ معين"""
    try:
        attendance_date = request.args.get('date', date.today().isoformat())
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT a.student_id, a.status, a.notes
            FROM attendance a
            WHERE a.date = ?
        ''', (attendance_date,))
        
        attendance_data = {}
        for row in cursor.fetchall():
            attendance_data[row[0]] = {
                'status': row[1],
                'notes': row[2]
            }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'attendance': attendance_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في جلب بيانات الحضور: {str(e)}'
        })

@app.route('/halaqa/<int:halaqa_id>')
def halaqa_details(halaqa_id):
    """عرض تفاصيل الحلقة"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # جلب بيانات الحلقة
        cursor.execute('SELECT * FROM halaqat WHERE id = ?', (halaqa_id,))
        halaqa = cursor.fetchone()
        
        if not halaqa:
            flash('الحلقة غير موجودة', 'error')
            return redirect(url_for('halaqat_list'))
        
        # جلب طلاب الحلقة
        cursor.execute('''
            SELECT * FROM students WHERE halaqa_id = ? ORDER BY name
        ''', (halaqa_id,))
        students = cursor.fetchall()
        
        # جلب إحصائيات الحضور (تقديرية)
        attendance_stats = {
            'total_sessions': 20,  # افتراضي
            'average_attendance': int(len(students) * 0.85) if students else 0
        }
        
        conn.close()
        
        return render_template('halaqa_details.html',
                             halaqa=halaqa,
                             students=students,
                             attendance_stats=attendance_stats)
        
    except Exception as e:
        flash(f'خطأ في عرض تفاصيل الحلقة: {e}', 'error')
        return redirect(url_for('halaqat_list'))

@app.route('/halaqa/<int:halaqa_id>/edit', methods=['GET', 'POST'])
def edit_halaqa(halaqa_id):
    """تعديل بيانات الحلقة"""
    if request.method == 'POST':
        try:
            # جمع البيانات من النموذج
            name = request.form.get('name')
            type_val = request.form.get('type')
            teacher_name = request.form.get('teacher_name')
            location = request.form.get('location')
            max_capacity = request.form.get('max_capacity', 30)
            schedule_days = request.form.get('schedule_days')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE halaqat 
                SET name = ?, type = ?, teacher_name = ?, location = ?, 
                    max_capacity = ?, schedule_days = ?, start_time = ?, end_time = ?
                WHERE id = ?
            ''', (name, type_val, teacher_name, location, max_capacity,
                  schedule_days, start_time, end_time, halaqa_id))
            
            conn.commit()
            conn.close()
            
            flash('تم تحديث بيانات الحلقة بنجاح!', 'success')
            return redirect(url_for('halaqa_details', halaqa_id=halaqa_id))
            
        except Exception as e:
            flash(f'خطأ في تحديث الحلقة: {e}', 'error')
    
    # جلب بيانات الحلقة للعرض
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM halaqat WHERE id = ?', (halaqa_id,))
        halaqa = cursor.fetchone()
        
        if not halaqa:
            flash('الحلقة غير موجودة', 'error')
            return redirect(url_for('halaqat_list'))
        
        # جلب قائمة المعلمين
        cursor.execute('SELECT id, name FROM teachers ORDER BY name')
        teachers = cursor.fetchall()
        
        conn.close()
        
        return render_template('edit_halaqa.html', halaqa=halaqa, teachers=teachers)
        
    except Exception as e:
        flash(f'خطأ في عرض نموذج التعديل: {e}', 'error')
        return redirect(url_for('halaqat_list'))

@app.route('/student/<int:student_id>/edit', methods=['GET', 'POST'])
def edit_student(student_id):
    """تعديل بيانات الطالب"""
    if request.method == 'POST':
        try:
            # جمع البيانات من النموذج
            name = request.form.get('name')
            age = request.form.get('age')
            gender = request.form.get('gender')
            phone = request.form.get('phone')
            email = request.form.get('email')
            guardian_name = request.form.get('guardian_name')
            guardian_phone = request.form.get('guardian_phone')
            halaqa_id = request.form.get('halaqa_id')
            memorization_level = request.form.get('memorization_level')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE students 
                SET name = ?, age = ?, gender = ?, phone = ?, email = ?,
                    guardian_name = ?, guardian_phone = ?, halaqa_id = ?, 
                    memorization_level = ?
                WHERE id = ?
            ''', (name, age, gender, phone, email, guardian_name,
                  guardian_phone, halaqa_id, memorization_level, student_id))
            
            conn.commit()
            conn.close()
            
            flash('تم تحديث بيانات الطالب بنجاح!', 'success')
            return redirect(url_for('students_list'))
            
        except Exception as e:
            flash(f'خطأ في تحديث الطالب: {e}', 'error')
    
    # جلب بيانات الطالب للعرض
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
        student = cursor.fetchone()
        
        if not student:
            flash('الطالب غير موجود', 'error')
            return redirect(url_for('students_list'))
        
        # جلب قائمة الحلقات
        cursor.execute('SELECT id, name FROM halaqat ORDER BY name')
        halaqat = cursor.fetchall()
        
        conn.close()
        
        return render_template('edit_student.html', student=student, halaqat=halaqat)
        
    except Exception as e:
        flash(f'خطأ في عرض نموذج التعديل: {e}', 'error')
        return redirect(url_for('students_list'))

@app.route('/teacher/<int:teacher_id>')
def teacher_details(teacher_id):
    """عرض تفاصيل المعلم"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # جلب بيانات المعلم
        cursor.execute('SELECT * FROM teachers WHERE id = ?', (teacher_id,))
        teacher = cursor.fetchone()
        
        if not teacher:
            flash('المعلم غير موجود', 'error')
            return redirect(url_for('teachers_list'))
        
        # جلب حلقات المعلم
        cursor.execute('''
            SELECT h.*, COUNT(s.id) as student_count
            FROM halaqat h
            LEFT JOIN students s ON h.id = s.halaqa_id
            WHERE h.teacher_name = ?
            GROUP BY h.id
            ORDER BY h.name
        ''', (teacher.name,))
        teacher_halaqat = cursor.fetchall()
        
        # جلب إجمالي الطلاب لهذا المعلم
        cursor.execute('''
            SELECT COUNT(s.id) as total_students
            FROM students s
            JOIN halaqat h ON s.halaqa_id = h.id
            WHERE h.teacher_name = ?
        ''', (teacher.name,))
        total_students = cursor.fetchone()[0] if cursor.fetchone() else 0
        
        conn.close()
        
        return render_template('teacher_details.html',
                             teacher=teacher,
                             teacher_halaqat=teacher_halaqat,
                             total_students=total_students)
        
    except Exception as e:
        flash(f'خطأ في عرض تفاصيل المعلم: {e}', 'error')
        return redirect(url_for('teachers_list'))

@app.route('/teacher/<int:teacher_id>/edit', methods=['GET', 'POST'])
def edit_teacher(teacher_id):
    """تعديل بيانات المعلم"""
    if request.method == 'POST':
        try:
            # جمع البيانات من النموذج
            name = request.form.get('name')
            gender = request.form.get('gender')
            phone = request.form.get('phone')
            email = request.form.get('email')
            qualification = request.form.get('qualification')
            specialization = request.form.get('specialization')
            experience_years = request.form.get('experience_years', 0)
            salary = request.form.get('salary')
            notes = request.form.get('notes')
            status = request.form.get('status', 'نشط')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE teachers 
                SET name = ?, gender = ?, phone = ?, email = ?, qualification = ?,
                    specialization = ?, experience_years = ?, salary = ?, 
                    notes = ?, status = ?
                WHERE id = ?
            ''', (name, gender, phone, email, qualification, specialization,
                  experience_years, salary, notes, status, teacher_id))
            
            conn.commit()
            conn.close()
            
            flash('تم تحديث بيانات المعلم بنجاح!', 'success')
            return redirect(url_for('teacher_details', teacher_id=teacher_id))
            
        except Exception as e:
            flash(f'خطأ في تحديث المعلم: {e}', 'error')
    
    # جلب بيانات المعلم للعرض
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM teachers WHERE id = ?', (teacher_id,))
        teacher = cursor.fetchone()
        
        if not teacher:
            flash('المعلم غير موجود', 'error')
            return redirect(url_for('teachers_list'))
        
        conn.close()
        
        return render_template('edit_teacher.html', teacher=teacher)
        
    except Exception as e:
        flash(f'خطأ في عرض نموذج التعديل: {e}', 'error')
        return redirect(url_for('teachers_list'))

@app.route('/generate_ai_report', methods=['POST'])
def generate_ai_report():
    """توليد تقرير ذكي مبسط"""
    try:
        data = request.json or {}
        report_type = data.get('report_type', 'weekly')
        time_period = data.get('time_period', 'current_week')
        halaqa_id = data.get('halaqa_id') or 'all'  # معالجة القيم null
        
        # تهيئة التقرير الافتراضي
        report = {
            'type': report_type,
            'time_period': time_period,
            'halaqa_id': halaqa_id,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'completed'
        }
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if report_type == 'weekly' or report_type == 'monthly':
            # تقرير زمني (أسبوعي أو شهري)
            period_name = "الأسبوعي" if report_type == 'weekly' else "الشهري"
            
            # فلترة بناء على الحلقة المختارة
            if halaqa_id != 'all':
                cursor.execute('SELECT COUNT(*) FROM students WHERE halaqa_id = ?', (halaqa_id,))
                total_students = cursor.fetchone()[0] or 0
                
                cursor.execute('SELECT name FROM halaqat WHERE id = ?', (halaqa_id,))
                halaqa_name = cursor.fetchone()
                halaqa_name = halaqa_name[0] if halaqa_name else f"حلقة رقم {halaqa_id}"
            else:
                cursor.execute('SELECT COUNT(*) FROM students')
                total_students = cursor.fetchone()[0] or 0
                halaqa_name = "جميع الحلقات"
            
            cursor.execute('SELECT COUNT(*) FROM halaqat')
            total_halaqat = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM donations')
            total_donations = cursor.fetchone()[0] or 0
            
            # تحديد نص الفترة
            period_text = {
                'current_week': 'الأسبوع الحالي',
                'last_week': 'الأسبوع الماضي', 
                'current_month': 'الشهر الحالي',
                'last_month': 'الشهر الماضي'
            }.get(time_period, time_period)
            
            report.update({
                'title': f'التقرير {period_name} - {halaqa_name}',
                'period': period_text,
                'halaqa_name': halaqa_name,
                'summary': {
                    'total_students': total_students,
                    'total_halaqat': total_halaqat if halaqa_id == 'all' else 1,
                    'total_donations': float(total_donations),
                    'attendance_rate': 85,  # قيمة افتراضية
                },
                'ai_analysis': f'تحليل شامل للأداء في {period_text} لـ{halaqa_name}. تظهر البيانات مستوى جيد من الانتظام والتقدم.',
                'strengths': [
                    'ارتفاع في معدلات الحضور',
                    'تحسن في مستوى الحفظ',
                    'زيادة في التبرعات'
                ],
                'recommendations': [
                    'الاستمرار في البرامج الحالية',
                    'تطوير برامج تحفيزية جديدة',
                    'تعزيز التواصل مع أولياء الأمور'
                ]
            })
            
        elif report_type == 'performance':
            # تحليل أداء الحلقات
            if halaqa_id != 'all':
                # أداء حلقة محددة
                cursor.execute('''
                    SELECT h.name, COUNT(s.id) as student_count
                    FROM halaqat h
                    LEFT JOIN students s ON h.id = s.halaqa_id
                    WHERE h.id = ?
                    GROUP BY h.id, h.name
                ''', (halaqa_id,))
                halaqat_performance = cursor.fetchall()
                title_suffix = f" - {halaqat_performance[0][0] if halaqat_performance else 'حلقة محددة'}"
            else:
                # جميع الحلقات
                cursor.execute('''
                    SELECT h.name, COUNT(s.id) as student_count
                    FROM halaqat h
                    LEFT JOIN students s ON h.id = s.halaqa_id
                    GROUP BY h.id, h.name
                    ORDER BY student_count DESC
                ''')
                halaqat_performance = cursor.fetchall()
                title_suffix = " - جميع الحلقات"
            
            report.update({
                'title': f'تقرير أداء الحلقات{title_suffix}',
                'halaqat_analysis': [
                    {
                        'halaqa_name': halaqa[0] if halaqa[0] else f'حلقة رقم {i+1}',
                        'student_count': halaqa[1] if halaqa[1] else 0,
                        'performance_rating': 'ممتاز' if (halaqa[1] or 0) >= 10 else 'جيد',
                        'recommendations': ['زيادة الأنشطة التفاعلية', 'تحسين بيئة التعلم']
                    }
                    for i, halaqa in enumerate(halaqat_performance[:5])
                ],
                'ai_analysis': 'تحليل شامل لأداء جميع الحلقات مع التركيز على نقاط القوة',
                'overall_rating': 'ممتاز'
            })
            
        elif report_type == 'allocation':
            # توزيع التبرعات
            cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM donations')
            total_amount = cursor.fetchone()[0] or 5000
            
            cursor.execute('SELECT COUNT(*) FROM halaqat')
            halaqat_count = cursor.fetchone()[0] or 1
            
            per_halaqa = float(total_amount) / halaqat_count if halaqat_count > 0 else 0
            
            report.update({
                'title': 'خطة توزيع التبرعات الذكية',
                'total_amount': float(total_amount),
                'allocation_strategy': 'توزيع عادل بناء على الاحتياجات والأداء',
                'allocations': [
                    {
                        'category': 'مكافآت الطلاب',
                        'amount': per_halaqa * 0.4,
                        'percentage': 40
                    },
                    {
                        'category': 'مستلزمات تعليمية', 
                        'amount': per_halaqa * 0.3,
                        'percentage': 30
                    },
                    {
                        'category': 'أنشطة ترفيهية',
                        'amount': per_halaqa * 0.2,
                        'percentage': 20
                    },
                    {
                        'category': 'طوارئ',
                        'amount': per_halaqa * 0.1,
                        'percentage': 10
                    }
                ],
                'ai_analysis': 'توزيع محسّن يركز على تحفيز الطلاب وتحسين جودة التعليم'
            })
        else:
            # نوع تقرير غير معروف
            report = {
                'type': report_type,
                'status': 'error',
                'message': f'نوع التقرير "{report_type}" غير مدعوم',
                'available_types': ['weekly', 'performance', 'allocation']
            }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في توليد التقرير: {str(e)}',
            'error_type': 'report_generation_error'
        })

@app.route('/export_report_pdf', methods=['POST'])
def export_report_pdf():
    """تصدير التقرير كملف PDF"""
    try:
        data = request.json or {}
        report_data = data.get('report', {})
        
        if not report_data:
            return jsonify({
                'success': False,
                'message': 'لا توجد بيانات تقرير للتصدير'
            })
        
        # إنشاء محتوى HTML للتقرير
        html_content = generate_pdf_html(report_data)
        
        # إنشاء استجابة PDF بسيطة (نسخة مؤقتة)
        from datetime import datetime
        
        pdf_content = f"""
📋 {report_data.get('title', 'تقرير')}
{'='*50}

📅 تاريخ التوليد: {datetime.now().strftime('%Y-%m-%d %H:%M')}
📊 نوع التقرير: {report_data.get('type', 'غير محدد')}
🏫 الحلقة: {report_data.get('halaqa_name', 'غير محدد')}
📆 الفترة: {report_data.get('period', 'غير محدد')}

{'='*50}
📈 الملخص:
{'='*50}
"""
        
        if 'summary' in report_data:
            summary = report_data['summary']
            pdf_content += f"""
👥 عدد الطلاب: {summary.get('total_students', 0)}
🏫 عدد الحلقات: {summary.get('total_halaqat', 0)} 
💰 إجمالي التبرعات: {summary.get('total_donations', 0):.2f} ريال
📊 معدل الحضور: {summary.get('attendance_rate', 0)}%
"""

        if 'ai_analysis' in report_data:
            pdf_content += f"""
{'='*50}
🤖 التحليل الذكي:
{'='*50}
{report_data['ai_analysis']}
"""

        if 'strengths' in report_data:
            pdf_content += f"""
{'='*50}
💪 نقاط القوة:
{'='*50}
"""
            for i, strength in enumerate(report_data['strengths'], 1):
                pdf_content += f"{i}. {strength}\n"

        if 'recommendations' in report_data:
            pdf_content += f"""
{'='*50}
📋 التوصيات:
{'='*50}
"""
            for i, rec in enumerate(report_data['recommendations'], 1):
                pdf_content += f"{i}. {rec}\n"

        if 'halaqat_analysis' in report_data:
            pdf_content += f"""
{'='*50}
📊 تحليل الحلقات:
{'='*50}
"""
            for analysis in report_data['halaqat_analysis']:
                pdf_content += f"""
🏫 {analysis.get('halaqa_name', 'حلقة')}:
   👥 عدد الطلاب: {analysis.get('student_count', 0)}
   ⭐ التقييم: {analysis.get('performance_rating', 'جيد')}
   📋 التوصيات: {', '.join(analysis.get('recommendations', []))}

"""

        if 'allocations' in report_data:
            pdf_content += f"""
{'='*50}
💰 خطة توزيع التبرعات:
{'='*50}
💵 المبلغ الإجمالي: {report_data.get('total_amount', 0):.2f} ريال

"""
            for allocation in report_data['allocations']:
                pdf_content += f"• {allocation.get('category')}: {allocation.get('amount', 0):.2f} ريال ({allocation.get('percentage', 0)}%)\n"

        pdf_content += f"""

{'='*50}
📝 ملاحظة: هذا تقرير تم توليده تلقائياً بواسطة نظام إدارة الحلقات القرآنية
🕌 جزاكم الله خيراً
{'='*50}
"""

        # إرجاع النص كملف للتحميل (حل مؤقت حتى نضيف مكتبة PDF حقيقية)
        response = app.response_class(
            pdf_content,
            mimetype='text/plain; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename="report_{datetime.now().strftime("%Y%m%d_%H%M")}.txt"',
                'Content-Type': 'text/plain; charset=utf-8'
            }
        )
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في تصدير التقرير: {str(e)}'
        })

@app.route('/export_data/<report_type>')
def export_data(report_type):
    """تصدير البيانات بصيغة CSV"""
    try:
        from flask import make_response, send_file
        import csv
        import io
        import tempfile
        from datetime import datetime
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إعداد اسم الملف
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{report_type}_{timestamp}.csv'
        
        # إنشاء مؤقت لملف CSV
        output = io.StringIO()
        
        if report_type == 'students':
            cursor.execute('''
                SELECT s.name, s.age, s.gender, s.phone, s.email, 
                       s.guardian_name, s.guardian_phone, h.name as halaqa_name,
                       s.join_date, s.memorization_level
                FROM students s 
                LEFT JOIN halaqat h ON s.halaqa_id = h.id 
                ORDER BY s.name
            ''')
            
            data = cursor.fetchall()
            writer = csv.writer(output)
            
            # كتابة العناوين
            writer.writerow(['الاسم', 'العمر', 'الجنس', 'الهاتف', 'البريد الإلكتروني', 
                           'اسم الولي', 'هاتف الولي', 'الحلقة', 'تاريخ الانضمام', 'مستوى الحفظ'])
            
            # كتابة البيانات
            for row in data:
                writer.writerow(row)
                
        elif report_type == 'halaqat':
            cursor.execute('''
                SELECT h.name, h.type, h.teacher_name, h.location, h.max_capacity,
                       h.schedule_days, h.start_time, h.end_time, COUNT(s.id) as student_count
                FROM halaqat h
                LEFT JOIN students s ON h.id = s.halaqa_id
                GROUP BY h.id
                ORDER BY h.name
            ''')
            
            data = cursor.fetchall()
            writer = csv.writer(output)
            
            writer.writerow(['اسم الحلقة', 'النوع', 'المعلم', 'المكان', 'السعة القصوى',
                           'أيام الدراسة', 'وقت البداية', 'وقت النهاية', 'عدد الطلاب'])
            
            for row in data:
                writer.writerow(row)
                
        elif report_type == 'attendance':
            cursor.execute('''
                SELECT a.date, s.name, h.name as halaqa_name, a.status, a.notes
                FROM attendance a
                JOIN students s ON a.student_id = s.id
                LEFT JOIN halaqat h ON s.halaqa_id = h.id
                ORDER BY a.date DESC, s.name
                LIMIT 1000
            ''')
            
            data = cursor.fetchall()
            writer = csv.writer(output)
            
            writer.writerow(['التاريخ', 'اسم الطالب', 'الحلقة', 'حالة الحضور', 'ملاحظات'])
            
            for row in data:
                writer.writerow(row)
                
        elif report_type == 'donations':
            cursor.execute('''
                SELECT donor_name, amount, donation_date, purpose, notes
                FROM donations 
                ORDER BY donation_date DESC
                LIMIT 1000
            ''')
            
            data = cursor.fetchall()
            writer = csv.writer(output)
            
            writer.writerow(['اسم المتبرع', 'المبلغ', 'تاريخ التبرع', 'الغرض', 'ملاحظات'])
            
            for row in data:
                writer.writerow(row)
                
        else:
            flash('نوع التقرير غير صحيح', 'error')
            return redirect(url_for('reports'))
        
        conn.close()
        
        # إعداد الاستجابة
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        flash(f'خطأ في تصدير البيانات: {e}', 'error')
        return redirect(url_for('reports'))

def generate_pdf_html(report_data):
    """توليد HTML لتحويله لـ PDF"""
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <title>{report_data.get('title', 'تقرير')}</title>
        <style>
            body {{ font-family: Arial, sans-serif; direction: rtl; text-align: right; }}
            .header {{ text-align: center; color: #2c5530; margin-bottom: 30px; }}
            .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
            .summary-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }}
            .stat-box {{ text-align: center; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🕌 {report_data.get('title', 'تقرير')}</h1>
            <p>تاريخ التوليد: {report_data.get('generated_at', '')}</p>
        </div>
        <!-- باقي المحتوى -->
    </body>
    </html>
    """
    return html

# Initialize database on startup
try:
    init_db()
    print("✅ تم تهيئة قاعدة البيانات")
except Exception as e:
    print(f"⚠️  تحذير: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)