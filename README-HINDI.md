# Stationery Hub — Python + Flask (Windows 11)

यह Python/Flask आधारित शुरुआती ई-कॉमर्स वेबसाइट है। इसमें प्रोडक्ट कैटलॉग, सर्च/कैटेगरी, कार्ट, COD checkout, SQLite database, Admin Login, प्रोडक्ट जोड़ना/एडिट करना/छिपाना, स्टॉक, ऑर्डर देखना और ऑर्डर स्टेटस बदलना शामिल है।

## Windows 11 पर चलाएँ
1. Python 3.11 या नया संस्करण https://www.python.org/downloads/windows/ से इंस्टॉल करें। इंस्टॉलर में **Add Python to PATH** चुनें।
2. इस ZIP को Extract करें।
3. `Stationery-Hub-Python` फोल्डर खोलें।
4. `run_windows.bat` पर डबल-क्लिक करें। या फोल्डर के address bar में `cmd` लिखकर:
   ```bat
   py -m pip install -r requirements.txt
   py app.py
   ```
5. Browser में http://127.0.0.1:5000 खोलें।

## Admin Login (पहली बार)
- URL: http://127.0.0.1:5000/admin/login
- Username: `admin`
- Password: `ChangeMe123!`

**सुरक्षा:** यह केवल स्थानीय development के लिए शुरुआती पासवर्ड है। इसे बदलने के लिए पहली बार DB बनने से पहले Windows Command Prompt में custom environment variables सेट करें:
```bat
set ADMIN_USERNAME=youradmin
set ADMIN_PASSWORD=use-a-long-unique-password
set SECRET_KEY=replace-with-a-long-random-secret
py app.py
```
अगर database पहले से बन चुका है, तो नया admin बनाने/पासवर्ड बदलने के लिए सुरक्षित password-reset सुविधा जोड़ें या database को हटाने से पहले ध्यान रखें कि इससे सभी products/orders मिट जाएँगे। Public internet पर default password कभी इस्तेमाल न करें।

## अभी क्या काम करता है
- Sample products स्वतः database में बनते हैं।
- Search और category filters।
- Session-based cart।
- COD checkout; order database में save होता है।
- ऑर्डर बनाते समय database transaction में stock और price दोबारा जाँचे जाते हैं।
- Admin product create/edit/disable, stock edit और order status update।
- SQLite database file `stationery_hub.db` में रहती है।

## अभी क्या बाकी है — public launch से पहले जरूरी
- **Online payment अभी चालू नहीं है।** Razorpay/अन्य gateway के लिए server-side order creation, signature verification और webhook लागू करना होगा। Secret keys browser/client में न रखें।
- यह demo में admin session authentication है, लेकिन production security hardening, CSRF protection, rate limiting, secure cookie settings, HTTPS और backups जरूरी हैं।
- Image URL फिलहाल इस्तेमाल होता है; admin image upload/storage सुविधा शामिल नहीं।
- Shipping fees, courier integration, email/SMS confirmations, cancellation/refund workflow, privacy policy, terms, GST/tax handling और customer order tracking जोड़ने होंगे।
- Flask development server को production में सीधे इस्तेमाल न करें। Python hosting (जैसे Render/PythonAnywhere/VPS) पर production WSGI server और environment variables के साथ deploy करें।
- SQLite छोटे शुरुआती परीक्षण के लिए है। बड़े/एकाधिक workers वाले live store में managed PostgreSQL बेहतर होगा।

## Internet पर live करने का सामान्य रास्ता
1. Code को private GitHub repository में डालें; database, `.env`, secrets या customer data upload न करें।
2. Python web hosting चुनें जो Flask/WSGI support करती हो।
3. `requirements.txt` से dependencies install हों; start command उदाहरण: `gunicorn app:app` (hosting में gunicorn dependency जोड़ें)।
4. `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` host के environment settings में दें।
5. Persistent storage configure करें; ephemeral filesystem पर SQLite orders स्थायी नहीं रहेंगे। बेहतर: PostgreSQL migrate करें।
6. HTTPS, admin password, CSRF, backups और order/payment tests के बाद ही real customers को URL दें।

**ध्यान दें:** यह शुरुआती working project है, पूर्ण production-ready marketplace नहीं। Real online payments और public launch से पहले सुरक्षा व payment integration पूरा करें।
