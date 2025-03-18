# دليل استخدام بوت الحماية لتطبيق LINE

## مقدمة
هذا الدليل يشرح كيفية نشر واستخدام بوت الحماية الخاص بتطبيق LINE. البوت مصمم لمساعدتك في إدارة وحماية مجموعاتك على تطبيق LINE.

## الميزات الرئيسية
1. **تتبع القراء والمتصلين بالمجموعة**: يقوم البوت بتسجيل من قرأ الرسائل في المجموعة
2. **الاستجابة للأمر `.r`**: عند إرسال هذا الأمر، يعرض البوت قائمة بمن قرأ آخر رسالة
3. **حماية مالك المجموعة**: يقوم البوت بإرسال تنبيه إذا تم طرد مالك المجموعة
4. **إدارة مخالفات قوانين المجموعة**: يساعد في تتبع الأعضاء الذين يخالفون قوانين المجموعة

## الأوامر المتاحة
- `.r` - عرض قائمة بمن قرأ آخر رسالة
- `.setowner` - تعيين المستخدم الحالي كمالك للمجموعة (للمسؤول فقط)
- `.help` - عرض رسالة المساعدة مع قائمة الأوامر المتاحة

## خطوات نشر البوت على Render

### 1. إعداد مستودع GitHub
1. قم بتسجيل الدخول إلى حساب GitHub الخاص بك
2. انقر على "+" في الزاوية العلوية اليمنى واختر "New repository"
3. أدخل اسم المستودع (مثل "line-protection-bot")
4. اختر "Public" أو "Private" حسب تفضيلاتك
5. انقر على "Create repository"
6. اتبع التعليمات لرفع الكود من جهازك المحلي:
   ```
   git remote add origin https://github.com/username/line-protection-bot.git
   git branch -M main
   git push -u origin main
   ```

### 2. نشر البوت على Render
1. قم بتسجيل الدخول إلى حساب Render الخاص بك
2. انقر على "New" واختر "Web Service"
3. اختر "Build and deploy from a Git repository"
4. اختر مستودع GitHub الذي أنشأته للبوت
5. أدخل المعلومات التالية:
   - Name: line-protection-bot
   - Region: اختر المنطقة الأقرب إليك
   - Branch: main
   - Runtime: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
6. في قسم "Environment Variables"، أضف المتغيرات التالية:
   - `CHANNEL_ACCESS_TOKEN`: قيمة الـ token الخاص بك
   - `CHANNEL_SECRET`: قيمة الـ secret الخاص بك
   - `USER_ID`: معرف المستخدم الخاص بك
   - `WEBHOOK_URL`: عنوان الـ webhook (سيكون عنوان Render + /callback)
7. انقر على "Create Web Service"

### 3. تكوين Webhook في LINE Developers
1. قم بتسجيل الدخول إلى [LINE Developers Console](https://developers.line.biz/console/)
2. اختر Provider ثم اختر القناة التي أنشأتها
3. انتقل إلى تبويب "Messaging API"
4. في قسم "Webhook URL"، أدخل عنوان الـ webhook الخاص بك:
   - `https://your-app-name.onrender.com/callback`
5. تأكد من تفعيل "Use webhook"
6. انقر على "Update" أو "Save" لحفظ التغييرات

## اختبار البوت
1. أضف البوت إلى إحدى مجموعاتك على LINE
2. أرسل رسالة `.help` للتحقق من أن البوت يعمل بشكل صحيح
3. جرب الأمر `.r` بعد إرسال بعض الرسائل للتحقق من وظيفة تتبع القراء
4. استخدم الأمر `.setowner` لتعيين نفسك كمالك للمجموعة

## استكشاف الأخطاء وإصلاحها
إذا واجهت أي مشاكل مع البوت:
1. تحقق من سجلات Render للبحث عن أي أخطاء
2. تأكد من صحة متغيرات البيئة
3. تحقق من إعدادات Webhook في LINE Developers
4. تأكد من أن البوت لديه الأذونات المناسبة في المجموعة

## ملاحظات أمنية
- احتفظ بـ Channel Access Token و Channel Secret بشكل آمن
- لا تشارك هذه المعلومات مع أي شخص
- استخدم دائماً اتصالاً آمناً (HTTPS) للـ webhook

## الدعم والمساعدة
إذا كنت بحاجة إلى مساعدة إضافية، يمكنك:
1. مراجعة [وثائق LINE Messaging API](https://developers.line.biz/en/docs/messaging-api/)
2. زيارة [منتدى LINE Developers](https://community.line.me/en/)
3. التواصل مع مطور البوت للحصول على الدعم
