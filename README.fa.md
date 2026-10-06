# خط لوله OEE → درآمد → حاشیه مشارکت (Contribution Margin)

**نسخه ۱٫۹٫۰٫۱** — کارخانه لبنی فرضی (North Valley Dairy)

پروژه پورتفولیو برای ترجمه افت عملیاتی (OEE) به شکاف واحد، موجودی، بازیابی، فروش ازدست‌رفته و **حاشیه مشارکت**.

> داده **مصنوعی** است. اعداد خروجی مدل‌اند، نه کارخانه واقعی و نه پیش‌بینی قطعی.

> **منبع اعداد:** [`final/Executive_Summary_Numbers.json`](final/Executive_Summary_Numbers.json)

## نتیجه کلیدی (اجرای مرجع)

- OEE وزنی زمانی: **۸۳٫۹۸٪**
- فرصت خالص CM مدل‌شده: حدود **۱٫۲۸ میلیون دلار**
- پس از holding افزایشی: حدود **۱٫۲۶M**
- پس از holding کل FG: حدود **۰٫۴۳M** (فقط زمینه)
- سهم مسیر OEE از کمبود بودجه CM: حدود **۵٫۶٪** (نه انتساب علّی کامل)

## اجرا

```bash
pip install -r requirements.txt
python run_pipeline.py
streamlit run dashboard/app.py
# فارسی:
streamlit run dashboard/app_fa.py
```

## هشدار

تا زمانی که `01` و `02` روی ریپو کامل نباشند، کلون به‌تنهایی end-to-end اجرا نمی‌شود. وضعیت: `UPLOAD_STATUS.md`
