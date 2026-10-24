import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "stationery_hub.db")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-development-secret-before-deploying")

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS products (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      category TEXT NOT NULL,
      description TEXT DEFAULT '',
      price REAL NOT NULL CHECK(price >= 0),
      image_url TEXT DEFAULT '',
      stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
      active INTEGER NOT NULL DEFAULT 1,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS orders (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_name TEXT NOT NULL,
      phone TEXT NOT NULL,
      address TEXT NOT NULL,
      city TEXT NOT NULL,
      pincode TEXT NOT NULL,
      payment_method TEXT NOT NULL DEFAULT 'COD',
      payment_status TEXT NOT NULL DEFAULT 'pending',
      status TEXT NOT NULL DEFAULT 'placed',
      total_amount REAL NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS order_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
      product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
      product_name TEXT NOT NULL,
      unit_price REAL NOT NULL,
      quantity INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS admins (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL
    );
    """)
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count == 0:
        sample = [
          ("Classic Ruled Notebook","Notebooks","Everyday ruled notebook for class and notes",65,"https://images.unsplash.com/photo-1531346878377-a5be20888e57?auto=format&fit=crop&w=800&q=85",50),
          ("Blue Ball Pens - Pack of 5","Pens","Smooth-writing blue ink pens",90,"https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?auto=format&fit=crop&w=800&q=85",30),
          ("HB Pencils - Pack of 10","Pencils","Reliable HB pencils for school and drawing",55,"https://images.unsplash.com/photo-1513364776144-60967b0f800f?auto=format&fit=crop&w=800&q=85",40),
          ("Geometry Box","School Supplies","Essential geometry tools for students",120,"https://images.unsplash.com/photo-1453738773917-9c3eff1db985?auto=format&fit=crop&w=800&q=85",18),
          ("Colour Pencil Set","Art Supplies","Colourful pencils for creative projects",160,"https://images.unsplash.com/photo-1513364776144-60967b0f800f?auto=format&fit=crop&w=800&q=85",20),
          ("Sticky Notes Set","Office Supplies","Bright notes for reminders and planning",75,"https://images.unsplash.com/photo-1517971129774-8a2b38fa128e?auto=format&fit=crop&w=800&q=85",25),
        ]
        conn.executemany("INSERT INTO products(name,category,description,price,image_url,stock) VALUES(?,?,?,?,?,?)", sample)
    # Initial development admin: change password after first login.
    if not conn.execute("SELECT id FROM admins LIMIT 1").fetchone():
        username = os.environ.get("ADMIN_USERNAME", "admin")
        password = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")
        conn.execute("INSERT INTO admins(username,password_hash) VALUES(?,?)",
                     (username, generate_password_hash(password)))
    conn.commit()
    conn.close()

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped

@app.template_filter("inr")
def inr(value):
    return "₹{:,.2f}".format(float(value or 0)).replace(".00", "")

@app.context_processor
def inject_cart_count():
    cart = session.get("cart", {})
    return {"cart_count": sum(int(q) for q in cart.values())}

@app.route("/")
def home():
    category = request.args.get("category", "All Items")
    search = request.args.get("q", "").strip()
    sql = "SELECT * FROM products WHERE active=1"
    args = []
    if category != "All Items":
        sql += " AND category=?"
        args.append(category)
    if search:
        sql += " AND (name LIKE ? OR category LIKE ? OR description LIKE ?)"
        like = f"%{search}%"
        args.extend([like, like, like])
    sql += " ORDER BY created_at DESC, id DESC"
    products = db().execute(sql, args).fetchall()
    categories = db().execute("SELECT DISTINCT category FROM products WHERE active=1 ORDER BY category").fetchall()
    return render_template("index.html", products=products, categories=categories,
                           selected_category=category, search=search)

@app.route("/cart")
def cart():
    cart_data = session.get("cart", {})
    items = []
    total = 0
    for pid, qty in cart_data.items():
        p = db().execute("SELECT * FROM products WHERE id=? AND active=1", (pid,)).fetchone()
        if p and int(qty) > 0:
            line = dict(product=p, qty=int(qty), subtotal=float(p["price"]) * int(qty))
            items.append(line)
            total += line["subtotal"]
    return render_template("cart.html", items=items, total=total)

@app.post("/cart/add/<int:product_id>")
def add_to_cart(product_id):
    p = db().execute("SELECT * FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
    if not p:
        flash("यह सामान उपलब्ध नहीं है।", "error")
        return redirect(url_for("home"))
    cart_data = session.get("cart", {})
    current = int(cart_data.get(str(product_id), 0))
    if current >= p["stock"]:
        flash("इस सामान का उपलब्ध स्टॉक इतना ही है।", "error")
    else:
        cart_data[str(product_id)] = current + 1
        session["cart"] = cart_data
        flash("सामान कार्ट में जोड़ दिया गया।", "success")
    return redirect(request.referrer or url_for("home"))

@app.post("/cart/update")
def update_cart():
    new_cart = {}
    for key, value in request.form.items():
        if key.startswith("qty_"):
            pid = key[4:]
            try:
                qty = max(0, min(99, int(value)))
            except ValueError:
                qty = 0
            p = db().execute("SELECT stock FROM products WHERE id=?", (pid,)).fetchone()
            if p and qty:
                new_cart[pid] = min(qty, int(p["stock"]))
    session["cart"] = new_cart
    flash("कार्ट अपडेट हो गया।", "success")
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart_data = session.get("cart", {})
    products, total = [], 0
    for pid, qty in cart_data.items():
        p = db().execute("SELECT * FROM products WHERE id=? AND active=1", (pid,)).fetchone()
        if p and int(qty) > 0:
            qty = min(int(qty), int(p["stock"]))
            products.append((p, qty))
            total += float(p["price"]) * qty
    if not products:
        flash("पहले कार्ट में सामान जोड़ें।", "error")
        return redirect(url_for("home"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        pincode = request.form.get("pincode", "").strip()
        payment = request.form.get("payment", "COD")
        if not name or not address or not city or not phone.isdigit() or len(phone) != 10 or not pincode.isdigit() or len(pincode) != 6:
            flash("कृपया नाम, 10 अंकों का मोबाइल, पता, शहर और 6 अंकों का PIN सही भरें।", "error")
            return render_template("checkout.html", products=products, total=total)
        if payment != "COD":
            flash("ऑनलाइन पेमेंट अभी सक्रिय नहीं है। असली भुगतान से पहले पेमेंट गेटवे और सर्वर-साइड सत्यापन जोड़ना होगा। फिलहाल COD चुनें।", "error")
            return render_template("checkout.html", products=products, total=total)
        conn = db()
        try:
            conn.execute("BEGIN IMMEDIATE")
            # Recheck stock and price inside the transaction; never trust submitted prices.
            verified = []
            verified_total = 0
            for p, qty in products:
                fresh = conn.execute("SELECT * FROM products WHERE id=? AND active=1", (p["id"],)).fetchone()
                if not fresh or fresh["stock"] < qty:
                    raise ValueError("स्टॉक बदल गया है। कार्ट अपडेट करके दोबारा कोशिश करें।")
                verified.append((fresh, qty))
                verified_total += float(fresh["price"]) * qty
            cur = conn.execute("""INSERT INTO orders(customer_name,phone,address,city,pincode,payment_method,payment_status,status,total_amount)
              VALUES(?,?,?,?,?,'COD','pending','placed',?)""",
              (name, phone, address, city, pincode, verified_total))
            order_id = cur.lastrowid
            for p, qty in verified:
                conn.execute("INSERT INTO order_items(order_id,product_id,product_name,unit_price,quantity) VALUES(?,?,?,?,?)",
                             (order_id, p["id"], p["name"], p["price"], qty))
                conn.execute("UPDATE products SET stock=stock-? WHERE id=?", (qty, p["id"]))
            conn.commit()
            session["cart"] = {}
            return render_template("order_success.html", order_id=order_id, total=verified_total)
        except ValueError as e:
            conn.rollback()
            flash(str(e), "error")
        except Exception:
            conn.rollback()
            app.logger.exception("Order creation failed")
            flash("ऑर्डर सेव नहीं हो पाया। कृपया फिर कोशिश करें।", "error")
    return render_template("checkout.html", products=products, total=total)

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = db()
    products = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 100").fetchall()
    stats = {
        "products": conn.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        "orders": conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        "sales": conn.execute("SELECT COALESCE(SUM(total_amount),0) FROM orders WHERE status!='cancelled'").fetchone()[0],
        "low_stock": conn.execute("SELECT COUNT(*) FROM products WHERE stock<=5 AND active=1").fetchone()[0]
    }
    return render_template("admin.html", products=products, orders=orders, stats=stats)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = db().execute("SELECT * FROM admins WHERE username=?", (username,)).fetchone()
        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            return redirect(url_for("admin_dashboard"))
        flash("यूज़रनेम या पासवर्ड गलत है।", "error")
    return render_template("admin_login.html")

@app.post("/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/admin/product/new", methods=["GET", "POST"])
@app.route("/admin/product/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def product_form(product_id=None):
    conn = db()
    product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone() if product_id else None
    if product_id and not product:
        flash("प्रोडक्ट नहीं मिला।", "error")
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        image_url = request.form.get("image_url", "").strip()
        try:
            price = float(request.form.get("price", ""))
            stock = int(request.form.get("stock", ""))
        except ValueError:
            flash("कीमत और स्टॉक सही भरें।", "error")
            return render_template("product_form.html", product=product)
        if not name or not category or price < 0 or stock < 0:
            flash("सभी जरूरी जानकारी सही भरें।", "error")
            return render_template("product_form.html", product=product)
        active = 1 if request.form.get("active") == "on" else 0
        if product:
            conn.execute("""UPDATE products SET name=?,category=?,description=?,price=?,image_url=?,stock=?,active=? WHERE id=?""",
                         (name, category, description, price, image_url, stock, active, product_id))
        else:
            conn.execute("""INSERT INTO products(name,category,description,price,image_url,stock,active) VALUES(?,?,?,?,?,?,?)""",
                         (name, category, description, price, image_url, stock, active))
        conn.commit()
        flash("प्रोडक्ट सेव हो गया।", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("product_form.html", product=product)

@app.post("/admin/product/<int:product_id>/delete")
@admin_required
def delete_product(product_id):
    db().execute("UPDATE products SET active=0 WHERE id=?", (product_id,))
    db().commit()
    flash("प्रोडक्ट स्टोर से छिपा दिया गया। पुराने ऑर्डर सुरक्षित रहेंगे।", "success")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/order/<int:order_id>/status")
@admin_required
def update_order_status(order_id):
    status = request.form.get("status", "")
    allowed = {"placed", "confirmed", "packed", "shipped", "delivered", "cancelled"}
    if status not in allowed:
        flash("गलत ऑर्डर स्टेटस।", "error")
    else:
        db().execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
        db().commit()
        flash("ऑर्डर स्टेटस अपडेट हो गया।", "success")
    return redirect(url_for("admin_dashboard"))

@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    init_db()
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
