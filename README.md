# 🕌 نظام إدارة الحلقات القرآنية

## 📋 الوصف
نظام شامل لإدارة الحلقات القرآنية يشمل:
- إدارة الطلاب والمعلمين
- تتبع الحضور والغياب
- إدارة التبرعات والحملات
- تقارير ذكية بالذكاء الاصطناعي

## 🚀 التشغيل المحلي

```bash
# استنساخ المشروع
git clone https://github.com/YOUR_USERNAME/islamic-education-system.git
cd islamic-education-system

# إنشاء بيئة افتراضية
python -m venv venv

# تفعيل البيئة الافتراضية
# في Windows:
venv\Scripts\activate
# في Linux/Mac:
source venv/bin/activate

# تثبيت المتطلبات
pip install -r requirements.txt

# تشغيل التطبيق
python app_simple.py
```

## 🌐 النشر على الإنترنت

### Render.com (مجاني):
1. Fork هذا المستودع
2. اذهب إلى https://render.com
3. New → Web Service → Connect GitHub
4. اختر المستودع
5. إعدادات النشر:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app_simple.py`

### Railway.app (مجاني):
1. اذهب إلى https://railway.app
2. New Project → Deploy from GitHub repo
3. اختر المستودع
4. انتظر النشر التلقائي

## 🛠️ التقنيات المستخدمة
- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: HTML, CSS, Bootstrap
- **UI**: Bootstrap RTL + Font Awesome

## 📊 المميزات
- ✅ إدارة شاملة للطلاب
- ✅ تتبع الحضور والغياب
- ✅ إدارة المعلمين والحلقات
- ✅ نظام التبرعات
- ✅ حملات جمع التبرعات
- ✅ تقارير تفصيلية
- ✅ واجهة عربية متجاوبة
- ✅ قاعدة بيانات محلية

## 📄 الترخيص
هذا المشروع مفتوح المصدر لخدمة المجتمع الإسلامي

## 🤝 المساهمة
نرحب بالمساهمات لتطوير هذا النظام وخدمة الحلقات القرآنية

---
**تم التطوير بـ ❤️ لخدمة كتاب الله الكريم**
