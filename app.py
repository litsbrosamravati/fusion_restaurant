# ==============================
# IMPORTS
# ==============================
from flask import (Flask, render_template, request, Response, redirect, session, url_for, flash, send_file, jsonify, make_response)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import io
from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from geopy.geocoders import Nominatim
import os
import uuid
import json
from decimal import Decimal
import math
import razorpay


# ==============================
# APP CONFIGURATION
# ==============================
app = Flask(__name__)
app.secret_key = "fusion_secret_key"

# ==============================
# PAYMENT GATEWAY
# ==============================
RAZORPAY_KEY_ID = "rzp_test_SPsNbr1p9JXcjC"        # Replace with your Razorpay key
RAZORPAY_KEY_SECRET = "pnOYyp6lyEq3tj39DcFZ8cwm"  # Replace with your Razorpay secret

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# ==============================
# MYSQL CONFIGURATION
# ==============================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'admin123'
app.config['MYSQL_DB'] = 'restaurant_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# ==============================
# DATABASE CONNECTION FUNCTION
# ==============================
def connect_db():
    return mysql.connection

# ==============================
# LANDING PAGE
# ==============================
@app.route("/")
def home():
    return render_template("Index.html")

# ------------------------------
# View Menu Page for visitors
# ------------------------------
@app.route("/menu")
def view_menu():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM menu WHERE status='Available'")
    menu_items = cur.fetchall()

    # Provide default image if none
    for item in menu_items:
        if not item.get("image"):
            item["image"] = "default.jpg"

    cur.close()

    # Pass Razorpay key to template
    return render_template(
        "menu.html",
        menu_items=menu_items,
        razorpay_key=RAZORPAY_KEY_ID
    )

# ------------------------------
# Create Razorpay Order
# ------------------------------
@app.route("/create_order", methods=["POST"])
def create_razorpay_order():
    try:
        data = request.get_json()
        total = data.get("total")  # in paise
        customer = data.get("customer")

        if not total or not customer:
            return jsonify({"error": "Invalid request"}), 400

        payment_order = razorpay_client.order.create({
            "amount": int(total),
            "currency": "INR",
            "payment_capture": 1
        })

        return jsonify(payment_order)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------------
# Place Visitor Order (After Payment)
# ------------------------------
@app.route("/place_visitor_order", methods=["POST"])
def place_visitor_order():
    try:
        data = request.get_json()
        name = data.get("name")
        email = data.get("email")
        phone = data.get("phone")
        table_no = data.get("table")
        cart = data.get("cart")
        payment_id = data.get("payment_id", None)

        if not name or not email or not phone or not cart:
            return jsonify({"error": "Missing required fields"}), 400

        # Calculate amounts
        total = sum(item["price"] * item["qty"] for item in cart)
        discount = 0
        if len(cart) >= 3:  # Example discount rule
            discount = total * 0.1
        final_amount = total - discount

        cur = mysql.connection.cursor()

        # Insert order
        cur.execute("""
            INSERT INTO visitor_orders
            (customer_name,email,phone,table_no,total_amount,discount,final_amount)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (name, email, phone, table_no, total, discount, final_amount))
        order_id = cur.lastrowid

        # Insert order items
        for item in cart:
            cur.execute("""
                INSERT INTO visitor_order_items
                (order_id,menu_item_id,quantity,price)
                VALUES (%s,%s,%s,%s)
            """, (order_id,item["id"],item["qty"],item["price"]))

        mysql.connection.commit()
        cur.close()

        return jsonify({"status": "success", "order_id": order_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------------
# View Receipt Page
# ------------------------------
@app.route("/receipt/<int:order_id>")
def receipt(order_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get order
    cur.execute("SELECT * FROM visitor_orders WHERE order_id=%s", (order_id,))
    order = cur.fetchone()

    # Get order items
    cur.execute("""
        SELECT voi.*, m.item_name 
        FROM visitor_order_items voi 
        JOIN menu m ON voi.menu_item_id = m.item_id 
        WHERE order_id=%s
    """, (order_id,))
    items = cur.fetchall()

    cur.close()
    return render_template("receipt.html", order=order, items=items)


# ------------------------------
# Download Receipt as PDF
# ------------------------------
@app.route("/download_receipt/<int:order_id>")
def download_receipt(order_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get order
    cur.execute("SELECT * FROM visitor_orders WHERE order_id=%s", (order_id,))
    order = cur.fetchone()

    # Get order items
    cur.execute("""
        SELECT voi.*, m.item_name 
        FROM visitor_order_items voi 
        JOIN menu m ON voi.menu_item_id = m.item_id 
        WHERE order_id=%s
    """, (order_id,))
    items = cur.fetchall()
    cur.close()

    # Build PDF with ReportLab
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)

    styles = getSampleStyleSheet()
    title_style   = ParagraphStyle('title',  parent=styles['Title'],
                                   fontSize=20, textColor=colors.HexColor('#1a1a1a'), spaceAfter=6)
    label_style   = ParagraphStyle('label',  parent=styles['Normal'],
                                   fontSize=10, textColor=colors.HexColor('#555555'))
    total_style   = ParagraphStyle('total',  parent=styles['Normal'],
                                   fontSize=11, alignment=TA_RIGHT, fontName='Helvetica-Bold')

    elements = []

    # Title
    elements.append(Paragraph("Restaurant Receipt", title_style))
    elements.append(Spacer(1, 4*mm))

    # Order details
    elements.append(Paragraph(f"<b>Order ID:</b> {order['order_id']}", label_style))
    elements.append(Paragraph(f"<b>Name:</b> {order['customer_name']}", label_style))
    elements.append(Paragraph(f"<b>Phone:</b> {order['phone']}", label_style))
    elements.append(Paragraph(f"<b>Email:</b> {order['email']}", label_style))
    elements.append(Spacer(1, 6*mm))

    # Items table
    table_data = [['Item', 'Qty', 'Price (₹)', 'Total (₹)']]
    for item in items:
        table_data.append([
            item['item_name'],
            str(item['quantity']),
            f"{float(item['price']):.2f}",
            f"{float(item['price']) * int(item['quantity']):.2f}"
        ])

    t = Table(table_data, colWidths=[80*mm, 20*mm, 35*mm, 35*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor('#28a745')),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0),  10),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  8),
        ('TOPPADDING',    (0, 0), (-1, 0),  8),
        ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',      (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f2f2')]),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('TOPPADDING',    (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('ALIGN',         (1, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 6*mm))

    # Totals
    elements.append(Paragraph(
        f"Total: ₹{float(order['total_amount']):.2f} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"Discount: ₹{float(order['discount']):.2f} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<font color='#28a745'>Final: ₹{float(order['final_amount']):.2f}</font>",
        total_style
    ))

    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, mimetype='application/pdf',
                     as_attachment=True,
                     download_name=f'Receipt_{order_id}.pdf')

# ==============================
# LOGIN
# ==============================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        role = request.form["role"]
        username = request.form["username"]
        password = request.form["password"]

        # =========================
        # ADMIN LOGIN
        # =========================
        if role == "admin":

            # Super Admin Login
            if username == "admin" and password == "super":
                session["user_id"] = "superadmin"
                session["role"] = "SuperAdmin"
                return redirect("/superadmin_dashboard")

            # Manager Login
            conn = connect_db()
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("""
            SELECT * FROM users
            WHERE email=%s
            AND role='Manager'
            AND status='Active'
            """, (username,))

            user = cursor.fetchone()

            if user and check_password_hash(user["password"], password):
                session["user_id"] = user["user_id"]
                session["role"] = "Manager"
                session["name"] = user["name"]
                return redirect("/manager/dashboard")

            cursor.close()

            return render_template("login.html", error="Invalid Admin Credentials")

        # =========================
        # EMPLOYEE LOGIN
        # =========================
        elif role == "employee":

            conn = connect_db()
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)

            # Get employee + employee_details
            cursor.execute("""
                SELECT u.*, e.employee_type, e.shift
                FROM users u
                LEFT JOIN employee_details e
                ON u.user_id = e.user_id
                WHERE u.email=%s
                AND u.role='Employee'
                AND u.status='Active'
            """, (username,))

            user = cursor.fetchone()
            cursor.close()

            if user and check_password_hash(user["password"], password):

                session["user_id"] = user["user_id"]
                session["role"] = "Employee"
                session["name"] = user["name"]
                # Normalize employee_type to consistent casing
                raw_type = (user["employee_type"] or "").strip()
                type_map = {"cook": "Cook", "waiter": "Waiter", "delivery boy": "Delivery Boy", "staff": "Staff"}
                session["employee_type"] = type_map.get(raw_type.lower(), raw_type)
                session["shift"] = user["shift"]

                # Redirect based on normalized session employee_type
                emp_type_norm = session["employee_type"]
                if emp_type_norm == "Cook":
                    return redirect("/cook/dashboard")
                elif emp_type_norm == "Delivery Boy":
                    return redirect("/delivery/dashboard")
                else:
                    return redirect("/waiter/dashboard")

            return render_template("login.html", error="Invalid Employee Credentials")

        # =========================
        # CUSTOMER LOGIN
        # =========================
        elif role == "customer":

            conn = connect_db()
            cursor = conn.cursor()

            cursor.execute("""
            SELECT * FROM users
            WHERE email=%s
            AND role='Customer'
            AND status='Active'
            """, (username,))

            user = cursor.fetchone()

            if user and check_password_hash(user["password"], password):
                session["user_id"] = user["user_id"]
                session["role"] = "Customer"

                return redirect("/customer/dashboard")

            cursor.close()

            return render_template("login.html", error="Invalid Customer Credentials")

    return render_template("login.html")
# ==============================
# CUSTOMER REGISTER
# ==============================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]

        # Structured address
        address_line = request.form.get("address_line")
        city = request.form.get("city")
        state = request.form.get("state")
        pincode = request.form.get("pincode")

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # GPS values
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")

        # Combine address
        full_address = f"{address_line}, {city}, {state} - {pincode}"

        # ==============================
        # VALIDATIONS
        # ==============================

        if password != confirm_password:
            flash("Passwords do not match!")
            return redirect("/register")

        # Require at least address or GPS
        if (not latitude or not longitude) and (not address_line or not city or not state or not pincode):
            flash("Please provide location using GPS or fill address manually.")
            return redirect("/register")

        # ==============================
        # CONVERT ADDRESS → LAT/LNG (if GPS not used)
        # ==============================

        latitude = None
        longitude = None

        # ==============================
        # TRY GPS FIRST (if user allowed)
        # ==============================
        if latitude and longitude:
            latitude = float(latitude)
            longitude = float(longitude)

        else:
            geolocator = Nominatim(user_agent="fusion_feast")

            try:
                # 1️⃣ Try FULL ADDRESS
                location = geolocator.geocode(full_address, timeout=10)

                # 2️⃣ If failed → try PINCODE ONLY
                if not location and pincode:
                    location = geolocator.geocode(f"{pincode}, India", timeout=10)

                # 3️⃣ If still failed → try CITY + PINCODE
                if not location:
                    location = geolocator.geocode(f"{city} {pincode}, India", timeout=10)

                if location:
                    latitude = float(location.latitude)
                    longitude = float(location.longitude)
                else:
                    latitude = None
                    longitude = None

            except Exception as e:
                print("Geocoding error:", e)
                latitude = None
                longitude = None
        # ==============================
        # DATABASE
        # ==============================

        conn = connect_db()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)

        # Check existing email
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            flash("Email already registered!")
            cursor.close()
            return redirect("/register")

        # Insert user
        hashed_password = generate_password_hash(password)

        cursor.execute("""
            INSERT INTO users
            (name, email, password, role, status, phone, address)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            name,
            email,
            hashed_password,
            "Customer",
            "Active",
            phone,
            full_address
        ))

        conn.commit()
        user_id = cursor.lastrowid

        # Insert customer
        cursor.execute("""
            INSERT INTO customers
            (customer_name, email, phone, user_id, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            name,
            email,
            phone,
            user_id,
            latitude,
            longitude
        ))

        conn.commit()
        cursor.close()

        flash("Registration successful! Please login.")
        return redirect("/login")

    return render_template("user/register.html")
# ==============================
# CUSTOMER DASHBOARD
# ==============================
from datetime import datetime, timedelta, time

@app.route("/customer/dashboard")
def customer_dashboard():

    user_id = session.get("user_id")

    if not user_id:
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    try:
        cursor.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
        user = cursor.fetchone()

        cursor.execute("""
            SELECT * FROM orders
            WHERE customer_id=%s
            ORDER BY order_date DESC
        """, (user_id,))
        orders = cursor.fetchall()

        cursor.execute("""
            SELECT tb.*, rt.table_number
            FROM table_bookings tb
            JOIN restaurant_tables rt
            ON tb.table_id = rt.table_id
            WHERE tb.customer_id=%s
            ORDER BY tb.booking_date DESC
        """, (user_id,))
        bookings = cursor.fetchall()

        now = datetime.now()

        for booking in bookings:

            booking_date = booking["booking_date"]
            booking_time = booking["booking_time"]

            if isinstance(booking_time, timedelta):
                seconds = booking_time.seconds
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                booking_time = time(hours, minutes)

            booking_datetime = datetime.combine(booking_date, booking_time)

            start_order_time = booking_datetime - timedelta(hours=1)
            cancel_limit = booking_datetime - timedelta(hours=6)

            # Order button logic
            if start_order_time <= now <= booking_datetime:
                booking["can_order"] = True
            else:
                booking["can_order"] = False

            # Cancel button logic
            if now < cancel_limit and booking["booking_status"] == "Booked":
                booking["can_cancel"] = True
            else:
                booking["can_cancel"] = False

    finally:
        cursor.close()

    return render_template(
        "user/dashboard_u.html",
        user=user,
        orders=orders,
        bookings=bookings
    )

# ==============================
# CANCEL ORDER
# ==============================
@app.route("/cancel_order/<int:order_id>")
def cancel_order(order_id):

    if session.get("role") != "Customer":
        return redirect("/login")

    user_id = session.get("user_id")

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # Check order status
    cursor.execute("""
        SELECT status FROM orders
        WHERE order_id=%s AND customer_id=%s
    """, (order_id, user_id))

    order = cursor.fetchone()

    if order and order["status"] == "Pending":

        cursor.execute("""
            UPDATE orders
            SET status='Cancelled'
            WHERE order_id=%s
        """, (order_id,))

        conn.commit()

    cursor.close()

    return redirect("/customer/dashboard")


# ==============================
# UPDATE CUSTOMER PROFILE
# ==============================
@app.route("/update_profile", methods=["POST"])
def update_profile():

    if session.get("role") != "Customer":
        return redirect("/login")

    name = request.form["name"]
    phone = request.form["phone"]
    address = request.form["address"]

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        UPDATE users
        SET name=%s, phone=%s, address=%s
        WHERE user_id=%s
    """, (name, phone, address, session["user_id"]))

    conn.commit()
    cursor.close()

    return redirect("/customer/dashboard")
# =========================================================
# CUSTOMER - ORDER ONLINE
# =========================================================
@app.route("/order_online", methods=["GET"])
def order_online():

    if session.get("role") != "Customer":
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # Menu
    cursor.execute("SELECT * FROM menu WHERE status='Available'")
    menu_items = cursor.fetchall()

    # Customer
    cursor.execute("""
        SELECT name, phone, address
        FROM users
        WHERE user_id=%s
    """, (session["user_id"],))
    customer = cursor.fetchone()

    # ✅ CART COUNT
    cursor.execute("""
        SELECT SUM(quantity) AS total_items
        FROM cart
        WHERE customer_id=%s
    """, (session["user_id"],))
    cart_count = cursor.fetchone()["total_items"] or 0

    cursor.close()

    return render_template(
        "user/order_online.html",
        menu_items=menu_items,
        customer=customer,
        cart_count=cart_count
    )
# =========================================================
# ADD TO CART (DATABASE BASED)
# =========================================================
@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():

    if session.get("role") != "Customer":
        return redirect("/login")

    item_id = request.form.get("item_id")
    customer_id = session["user_id"]

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT * FROM cart
        WHERE customer_id=%s AND item_id=%s
    """,(customer_id,item_id))

    cart_item = cursor.fetchone()

    if cart_item:
        cursor.execute("""
            UPDATE cart
            SET quantity = quantity + 1
            WHERE cart_id=%s
        """,(cart_item["cart_id"],))
    else:
        cursor.execute("""
            INSERT INTO cart (customer_id,item_id,quantity)
            VALUES (%s,%s,1)
        """,(customer_id,item_id))

    conn.commit()
    cursor.close()

    flash("✅ Item added to cart!", "success")   # 🔥 IMPORTANT

    return redirect("/order_online")

# =========================================================
# VIEW CART (DATABASE)
# =========================================================
@app.route("/cart")
def view_cart():

    if session.get("role") != "Customer":
        return redirect("/login")

    customer_id = session["user_id"]

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT c.cart_id,
               c.quantity,
               m.item_id,
               m.item_name,
               m.price,
               m.image
        FROM cart c
        JOIN menu m ON c.item_id = m.item_id
        WHERE c.customer_id=%s
    """,(customer_id,))

    cart_items = cursor.fetchall()

    cursor.execute("SELECT name, phone FROM users WHERE user_id=%s", (customer_id,))
    customer = cursor.fetchone()

    cursor.close()

    total = sum(item["price"] * item["quantity"] for item in cart_items)

    return render_template(
        "user/cart.html",
        cart=cart_items,
        total=total,
        customer=customer
    )
@app.route("/update_cart_quantity", methods=["POST"])
def update_cart_quantity():

    item_id = request.form.get("item_id")
    action = request.form.get("action")
    customer_id = session["user_id"]

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT * FROM cart
        WHERE customer_id=%s AND item_id=%s
    """, (customer_id, item_id))

    item = cursor.fetchone()

    if item:
        if action == "increase":
            cursor.execute("""
                UPDATE cart SET quantity = quantity + 1
                WHERE cart_id=%s
            """, (item["cart_id"],))

        elif action == "decrease":
            if item["quantity"] > 1:
                cursor.execute("""
                    UPDATE cart SET quantity = quantity - 1
                    WHERE cart_id=%s
                """, (item["cart_id"],))
            else:
                cursor.execute("""
                    DELETE FROM cart WHERE cart_id=%s
                """, (item["cart_id"],))

    conn.commit()
    cursor.close()

    return redirect("/cart")
# =========================================================
# REMOVE FROM CART
# =========================================================
@app.route("/remove_from_cart/<int:item_id>")
def remove_from_cart(item_id):

    if session.get("role") != "Customer":
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM cart
        WHERE customer_id=%s AND item_id=%s
    """,(session["user_id"],item_id))

    conn.commit()
    cursor.close()

    return redirect("/cart")
# =========================================================
# CHECKOUT (CREATE RAZORPAY ORDER)
# =========================================================
@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    if session.get("role") != "Customer":
        return redirect("/login")

    if request.method == "GET":
        return redirect("/cart")

    from geopy.geocoders import Nominatim

    # ================= RESTAURANT LOCATION =================
    RESTAURANT_LAT = 20.95024323751783
    RESTAURANT_LNG = 77.76437642082739
    MAX_DISTANCE_KM = 10

    # ================= DISTANCE FUNCTION =================
    def calculate_distance(lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat/2)**2 +
             math.cos(math.radians(lat1)) *
             math.cos(math.radians(lat2)) *
             math.sin(dlon/2)**2)

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    # ================= GET FORM DATA =================
    address = request.form.get("address")
    lat = request.form.get("lat")
    lng = request.form.get("lng")

    if not address:
        flash("Please enter delivery address", "danger")
        return redirect("/cart")

    # ================= GET USER LOCATION =================
    try:
        if lat and lng:
            # ✅ BEST CASE: GPS AVAILABLE
            user_lat = float(lat)
            user_lng = float(lng)

        else:
            # ⚠️ FALLBACK: GEOCODING
            full_address = address + ", India"

            geolocator = Nominatim(user_agent="food_delivery_app", timeout=5)
            location = geolocator.geocode(full_address, exactly_one=True)

            if not location:
                flash("Invalid address. Please enter a proper location.", "danger")
                return redirect("/cart")

            user_lat = location.latitude
            user_lng = location.longitude

    except Exception as e:
        print("LOCATION ERROR:", e)
        flash("Error fetching location. Try again.", "danger")
        return redirect("/cart")

    # ================= DISTANCE CHECK =================
    distance = calculate_distance(RESTAURANT_LAT, RESTAURANT_LNG, user_lat, user_lng)

    print("DISTANCE:", distance)

    if distance > MAX_DISTANCE_KM:
        flash("❌ Cannot deliver beyond 10 km from restaurant", "danger")
        return redirect("/cart")

    # ================= DATABASE =================
    customer_id = session["user_id"]

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT c.quantity,
               m.item_id,
               m.item_name,
               m.price
        FROM cart c
        JOIN menu m ON c.item_id = m.item_id
        WHERE c.customer_id=%s
    """, (customer_id,))

    cart_items = cursor.fetchall()

    if not cart_items:
        cursor.close()
        return redirect("/cart")

    total = sum(float(item["price"]) * item["quantity"] for item in cart_items)

    # ================= CREATE RAZORPAY ORDER =================
    razorpay_order = razorpay_client.order.create({
        "amount": int(total * 100),
        "currency": "INR",
        "payment_capture": 1
    })

    razorpay_order_id = razorpay_order["id"]

    # ================= STORE SESSION =================
    session["pending_payment"] = {
        "cart": cart_items,
        "total": total,
        "razorpay_order_id": razorpay_order_id,
        "source": "cart",
        "address": address,
        "lat": user_lat,
        "lng": user_lng
    }

    cursor.close()

    return render_template(
        "user/pay_order.html",
        razorpay_key=RAZORPAY_KEY_ID,
        razorpay_order_id=razorpay_order_id,
        amount=int(total * 100),
        source="cart"
    )


@app.route("/verify_order_payment", methods=["POST"])
def verify_order_payment():
    if session.get("role") != "Customer":
        return redirect("/login")

    payment_id = request.form.get("razorpay_payment_id")
    razorpay_order_id = request.form.get("razorpay_order_id")
    signature = request.form.get("razorpay_signature")

    try:
        # ================= VERIFY PAYMENT =================
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        })

        # ================= GET SESSION DATA =================
        data = session.get("pending_payment")

        if not data:
            flash("Session expired. Please try again.", "danger")
            return redirect("/cart")

        cart = data.get("cart", [])
        total = data.get("total", 0)
        address = data.get("address")

        # ✅ NEW: GET LAT & LNG FROM SESSION
        lat = data.get("lat")
        lng = data.get("lng")

        if not cart or not address:
            flash("Invalid order data. Please try again.", "danger")
            return redirect("/cart")

        conn = connect_db()
        cursor = conn.cursor()

        # ================= PREVENT DUPLICATE =================
        cursor.execute("""
            SELECT order_id FROM orders WHERE razorpay_payment_id=%s
        """, (payment_id,))

        if cursor.fetchone():
            flash("Order already processed!", "info")
            return redirect("/customer/dashboard")

        # ================= CREATE ORDER (UPDATED) =================
        cursor.execute("""
            INSERT INTO orders
            (customer_id,total_amount,payment_method,payment_status,status,
             order_date,razorpay_order_id,razorpay_payment_id,
             delivery_address,latitude,longitude)

            VALUES (%s,%s,'UPI','Paid','Pending',NOW(),%s,%s,%s,%s,%s)
        """, (
            session["user_id"],
            total,
            razorpay_order_id,
            payment_id,
            address,
            lat,  # ✅ SAVED
            lng  # ✅ SAVED
        ))

        order_id_db = cursor.lastrowid

        # ================= INSERT ORDER ITEMS =================
        for item in cart:
            cursor.execute("""
                INSERT INTO order_items
                (order_id,item_id,quantity,price)
                VALUES (%s,%s,%s,%s)
            """, (
                order_id_db,
                item["item_id"],
                item["quantity"],
                item["price"]
            ))

        # ================= CLEAR CART =================
        cursor.execute("""
            DELETE FROM cart
            WHERE customer_id=%s
        """, (session["user_id"],))

        conn.commit()
        cursor.close()

        # ================= CLEAR SESSION =================
        session.pop("pending_payment", None)
        session.pop("cart", None)

        flash("🎉 Order placed successfully!", "success")
        return redirect("/customer/dashboard")

    except razorpay.errors.SignatureVerificationError:
        flash("❌ Payment verification failed", "danger")
        return redirect("/cart")

    except Exception as e:
        print("ERROR:", e)
        flash("Something went wrong. Try again.", "danger")
        return redirect("/cart")
# =========================================================
# PAYMENT CANCELLED
# =========================================================
@app.route("/payment_cancelled")
def payment_cancelled():

    source = request.args.get("source")

    # ===============================
    # TABLE BOOKING CANCELLED
    # ===============================
    if source == "table":
        flash("❌ Table booking payment cancelled.", "danger")
        return redirect("/table_booking")

    # ===============================
    # SINGLE ORDER (BUY NOW)
    # ===============================
    elif source == "single":
        flash("❌ Payment cancelled. Your order was not placed.", "danger")
        return redirect("/order_online")

    # ===============================
    # CART PAYMENT CANCELLED
    # ===============================
    else:
        flash("❌ Payment cancelled. Your order was not placed.", "danger")
        return redirect("/cart")
# =========================================================
# TABLE BOOKING WITH RAZORPAY PAYMENT
# =========================================================
@app.route("/table_booking", methods=["GET", "POST"])
def table_booking():

    if session.get("role") != "Customer":
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    now = datetime.now()

    # ============================================
    # GET TABLES + CURRENT BOOKINGS
    # ============================================
    cursor.execute("""
        SELECT t.*,
               b.booking_date,
               b.booking_time,
               DATE_ADD(CONCAT(b.booking_date,' ',b.booking_time), INTERVAL 2 HOUR) AS end_time
        FROM restaurant_tables t
        LEFT JOIN table_bookings b
        ON t.table_id = b.table_id AND b.booking_status='Booked'
        ORDER BY t.table_number ASC
    """)

    tables = cursor.fetchall()

    available_tables = []
    booked_tables = []

    # ============================================
    # SEPARATE AVAILABLE AND BOOKED TABLES
    # ============================================
    for t in tables:

        # convert booking_date
        if t["booking_date"] and isinstance(t["booking_date"], str):
            t["booking_date"] = datetime.strptime(t["booking_date"], "%Y-%m-%d")

        # convert booking_time
        if t["booking_time"] and isinstance(t["booking_time"], str):
            t["booking_time"] = datetime.strptime(t["booking_time"], "%H:%M:%S")

        # convert end_time
        if t["end_time"] and isinstance(t["end_time"], str):
            t["end_time"] = datetime.strptime(t["end_time"], "%Y-%m-%d %H:%M:%S")

        if t["booking_date"] and t["end_time"]:

            if t["end_time"] > now:
                booked_tables.append(t)
            else:
                available_tables.append(t)

        else:
            available_tables.append(t)
    # ============================================
    # HANDLE BOOKING FORM
    # ============================================
    if request.method == "POST":

        table_id = int(request.form.get("table_id"))
        booking_date = request.form.get("booking_date")
        booking_time = request.form.get("booking_time")
        guests = int(request.form.get("guests"))

        if not table_id or not booking_date or not booking_time or not guests:
            flash("All fields are required", "danger")
            return redirect("/table_booking")

        selected_datetime = f"{booking_date} {booking_time}"

        # ============================================
        # CHECK BOOKING CONFLICT
        # ============================================
        cursor.execute("""
            SELECT * FROM table_bookings
            WHERE table_id=%s
            AND booking_status='Booked'
            AND %s BETWEEN CONCAT(booking_date,' ',booking_time)
            AND DATE_ADD(CONCAT(booking_date,' ',booking_time), INTERVAL 2 HOUR)
        """,(table_id, selected_datetime))

        conflict = cursor.fetchone()

        if conflict:
            flash("Table already booked at this time.", "danger")
            return redirect("/table_booking")

        # ============================================
        # GET TABLE PRICE
        # ============================================
        cursor.execute("""
            SELECT capacity, price_per_person
            FROM restaurant_tables
            WHERE table_id=%s
        """,(table_id,))

        table = cursor.fetchone()

        total_price = table["price_per_person"] * guests

        if guests < table["capacity"]:
            total_price = total_price * Decimal("0.9")

        # ============================================
        # CREATE RAZORPAY ORDER
        # ============================================
        razorpay_order = razorpay_client.order.create({
            "amount": int(total_price * 100),
            "currency": "INR",
            "payment_capture": 1
        })

        razorpay_order_id = razorpay_order["id"]

        cursor.close()

        # ============================================
        # OPEN PAYMENT PAGE
        # ============================================
        return render_template(
            "user/pay_booking.html",
            razorpay_key=RAZORPAY_KEY_ID,
            razorpay_order_id=razorpay_order_id,
            amount=int(total_price * 100),
            table_id=table_id,
            booking_date=booking_date,
            booking_time=booking_time,
            guests=guests,
            total_price=total_price
        )

    cursor.close()

    return render_template(
        "user/table_booking.html",
        available_tables=available_tables,
        booked_tables=booked_tables,
        current_time=now
    )
# =========================================================
# VERIFY BOOKING PAYMENT (RAZORPAY)
# =========================================================
@app.route("/verify_booking_payment", methods=["POST"])
def verify_booking_payment():

    data = request.get_json(silent=True) or request.form

    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature")

    table_id = data.get("table_id")
    booking_date = data.get("booking_date")
    booking_time = data.get("booking_time")
    guests = data.get("guests")
    total_price = data.get("total_price")

    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        })

        conn = connect_db()
        cursor = conn.cursor()

        # =============================
        # SAVE BOOKING
        # =============================
        cursor.execute("""
            INSERT INTO table_bookings
            (customer_id, table_id, booking_date, booking_time, guests,
             booking_status, payment_status, total_price,
             razorpay_order_id, razorpay_payment_id)
            VALUES (%s,%s,%s,%s,%s,'Booked','Paid',%s,%s,%s)
        """, (
            session["user_id"],
            table_id,
            booking_date,
            booking_time,
            guests,
            total_price,
            razorpay_order_id,
            razorpay_payment_id
        ))

        # =============================
        # SEND NOTIFICATION
        # =============================
        message = f"New table booking for Table {table_id} on {booking_date} at {booking_time}"

        cursor.execute("""
            INSERT INTO notifications (employee_id, message)
            VALUES (%s,%s)
        """, (session["user_id"], message))

        conn.commit()
        cursor.close()

        flash("Table booking confirmed successfully!", "success")

        # =============================
        # REDIRECT USER
        # =============================
        return redirect("/table_booking")

    except Exception as e:
        flash("Payment verification failed!", "danger")
        return redirect("/table_booking")

#canceltableby customer
@app.route("/cancel_booking/<int:booking_id>")
def cancel_booking(booking_id):

    if session.get("role") != "Customer":
        return redirect("/login")

    user_id = session.get("user_id")

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT booking_status, booking_date, booking_time
        FROM table_bookings
        WHERE booking_id=%s AND customer_id=%s
    """,(booking_id,user_id))

    booking = cursor.fetchone()

    if booking and booking["booking_status"] == "Booked":

        booking_date = booking["booking_date"]
        booking_time = booking["booking_time"]

        # convert timedelta to time if needed
        if isinstance(booking_time, timedelta):
            seconds = booking_time.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            booking_time = time(hours, minutes)

        booking_datetime = datetime.combine(booking_date, booking_time)
        now = datetime.now()

        time_difference = booking_datetime - now

        if time_difference >= timedelta(hours=6):

            cursor.execute("""
                UPDATE table_bookings
                SET booking_status='Cancelled'
                WHERE booking_id=%s
            """,(booking_id,))

            conn.commit()
            flash("Booking cancelled successfully.", "success")

        else:
            flash("Booking can only be cancelled 6 hours before the reservation time.", "danger")

    else:
        flash("Invalid booking.", "danger")

    cursor.close()

    return redirect("/customer/dashboard")
# =========================================================
# ORDER FROM BOOKED TABLE (MENU PAGE)
# =========================================================
@app.route("/order-from-table/<int:booking_id>")
def order_from_table(booking_id):

    if session.get("role") != "Customer":
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT * FROM table_bookings
        WHERE booking_id=%s AND customer_id=%s
        AND booking_status='Booked'
    """,(booking_id, session["user_id"]))

    booking = cursor.fetchone()

    if not booking:
        cursor.close()
        return "Booking not found!",404

    table_id = booking["table_id"]
    session["table_id"] = table_id
    session["booking_id"] = booking_id

    # menu items
    cursor.execute("SELECT * FROM menu WHERE status='Available'")
    menu_items = cursor.fetchall()

    # cart count
    cursor.execute("""
        SELECT SUM(quantity) as total
        FROM cart
        WHERE customer_id=%s
    """,(session["user_id"],))

    cart = cursor.fetchone()
    cart_count = cart["total"] if cart["total"] else 0

    cursor.close()

    return render_template(
        "user/order_from_table.html",
        menu_items=menu_items,
        table_id=table_id,
        cart_count=cart_count
    )
# =========================================================
# ADD ITEM TO CART (TABLE ORDER)
# =========================================================
@app.route("/add-to-cart-table/<int:item_id>", methods=["POST"])
def add_to_cart_table(item_id):

    print("ADD TO CART HIT")   # DEBUG LINE

    if session.get("role") != "Customer":
        return redirect("/login")

    customer_id = session["user_id"]

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM cart
        WHERE customer_id=%s AND item_id=%s
    """,(customer_id,item_id))

    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE cart
            SET quantity = quantity + 1
            WHERE customer_id=%s AND item_id=%s
        """,(customer_id,item_id))
    else:
        cursor.execute("""
            INSERT INTO cart (customer_id,item_id,quantity)
            VALUES (%s,%s,1)
        """,(customer_id,item_id))

    conn.commit()
    cursor.close()

    print("ITEM ADDED")   # DEBUG

    return redirect(request.referrer)
# =========================================================
# VIEW TABLE CART
# =========================================================
@app.route("/view-table-cart")
def view_table_cart():

    if session.get("role") != "Customer":
        return redirect("/login")

    customer_id = session["user_id"]
    table_id = session.get("table_id")
    booking_id = session.get("booking_id")

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT c.*, m.item_name, m.price
        FROM cart c
        JOIN menu m ON c.item_id = m.item_id
        WHERE c.customer_id=%s
    """,(customer_id,))

    cart_items = cursor.fetchall()

    cursor.close()

    return render_template(
        "user/table_cart.html",
        cart_items=cart_items,
        table_id=table_id,
        booking_id=booking_id
    )
@app.route("/update-table-cart/<int:cart_id>", methods=["POST"])
def update_table_cart(cart_id):

    action = request.form.get("action")

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)  # FIX: DictCursor needed for row["quantity"]

    if action == "increase":
        cursor.execute("""
        UPDATE cart
        SET quantity = quantity + 1
        WHERE cart_id=%s
        """,(cart_id,))

    elif action == "decrease":

        cursor.execute("SELECT quantity FROM cart WHERE cart_id=%s", (cart_id,))
        row = cursor.fetchone()
        qty = row["quantity"]

        if qty > 1:
            cursor.execute("""
            UPDATE cart
            SET quantity = quantity - 1
            WHERE cart_id=%s
            """,(cart_id,))
        else:
            cursor.execute("DELETE FROM cart WHERE cart_id=%s",(cart_id,))

    conn.commit()
    cursor.close()

    return redirect("/view-table-cart")
@app.route("/remove-table-cart/<int:cart_id>", methods=["POST"])
def remove_table_cart(cart_id):

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM cart WHERE cart_id=%s",(cart_id,))

    conn.commit()
    cursor.close()

    return redirect("/view-table-cart")
# =========================================================
# PAY TABLE ORDER (RAZORPAY)
# =========================================================
@app.route("/pay-table-order/<int:table_id>")
def pay_table_order(table_id):

    if session.get("role") != "Customer":
        return redirect("/login")

    customer_id = session["user_id"]

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT c.*, m.price
        FROM cart c
        JOIN menu m ON c.item_id = m.item_id
        WHERE c.customer_id=%s
    """,(customer_id,))

    cart_items = cursor.fetchall()

    total = 0

    for item in cart_items:
        total += item["price"] * item["quantity"]

    razorpay_order = razorpay_client.order.create({
        "amount": int(total * 100),
        "currency": "INR",
        "payment_capture": 1
    })

    # FIX: Store razorpay_order_id in session so verify route can cross-check it
    session["pending_table_payment"] = {
        "razorpay_order_id": razorpay_order["id"],
        "table_id": table_id,
        "amount": int(total * 100)
    }

    return render_template(
        "user/pay_table_order.html",
        amount=int(total * 100),
        razorpay_order_id=razorpay_order["id"],
        table_id=table_id,
        razorpay_key=RAZORPAY_KEY_ID
    )

@app.route("/verify-table-payment", methods=["POST"])
def verify_table_payment():
    try:
        # ── 1. Parse incoming JSON ──────────────────────────────────────────
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"status": "error", "message": "Invalid request body"}), 400

        payment_id = data.get("razorpay_payment_id")
        rzp_order_id = data.get("razorpay_order_id")
        signature = data.get("razorpay_signature")

        if not payment_id or not rzp_order_id or not signature:
            return jsonify({"status": "error", "message": "Missing payment fields"}), 400

        # ── 2. Session safety ───────────────────────────────────────────────
        customer_id = session.get("user_id")
        if not customer_id:
            return jsonify({"status": "error", "message": "Session expired. Please log in again."}), 401

        # Get table_id from session (stored by pay_table_order route)
        pending = session.get("pending_table_payment", {})
        table_id = pending.get("table_id") or session.get("table_id")

        if not table_id:
            return jsonify({"status": "error", "message": "Table session lost. Please restart checkout."}), 400

        # ── 3. Razorpay signature verification (THE CRITICAL FIX) ──────────
        try:
            razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id":   rzp_order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature":  signature
            })
        except razorpay.errors.SignatureVerificationError:
            return jsonify({"status": "error", "message": "Payment signature verification failed."}), 400

        # ── 4. Fetch cart ───────────────────────────────────────────────────
        conn = connect_db()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("""
            SELECT c.*, m.item_id, m.price
            FROM cart c
            JOIN menu m ON c.item_id = m.item_id
            WHERE c.customer_id=%s
        """, (customer_id,))
        cart_items = cursor.fetchall()

        if not cart_items:
            cursor.close()
            return jsonify({"status": "error", "message": "Cart is empty or already checked out."}), 400

        total = sum(float(item["price"]) * int(item["quantity"]) for item in cart_items)

        # ── 5. Insert order ─────────────────────────────────────────────────
        cursor.execute("""
            INSERT INTO orders
            (customer_id, total_amount, payment_method, payment_status,
             status, order_type, table_id,
             razorpay_order_id, razorpay_payment_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            customer_id,
            total,
            "UPI",
            "Paid",
            "Pending",
            "Table",
            table_id,
            rzp_order_id,
            payment_id
        ))

        new_order_id = cursor.lastrowid

        # ── 6. Insert order items ───────────────────────────────────────────
        for item in cart_items:
            cursor.execute("""
                INSERT INTO order_items (order_id, item_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            """, (new_order_id, item["item_id"], item["quantity"], item["price"]))

        # ── 7. Clear cart ───────────────────────────────────────────────────
        cursor.execute("DELETE FROM cart WHERE customer_id=%s", (customer_id,))

        conn.commit()
        cursor.close()

        # ── 8. Clean up session ─────────────────────────────────────────────
        session.pop("pending_table_payment", None)
        session.pop("table_id", None)
        session.pop("booking_id", None)
        session["order_success"] = f"🎉 Order #{new_order_id} placed! Your food is being prepared."

        return jsonify({"status": "success", "order_id": new_order_id})

    except Exception as e:
        # Always return JSON so the frontend .then(r => r.json()) never crashes
        print(f"[verify_table_payment] ERROR: {e}")
        return jsonify({"status": "error", "message": "Server error. Please contact support."}), 500

# ============================================================
# CUSTOMER: ORDER HISTORY PAGE
# ============================================================
@app.route("/order-history")
def order_history():
    if session.get("role") != "Customer":
        return redirect("/login")

    user_id = session["user_id"]
    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT * FROM orders
        WHERE customer_id=%s
        ORDER BY order_date DESC
    """, (user_id,))
    orders = cursor.fetchall()
    cursor.close()

    return render_template("user/order_history.html", orders=orders)


# ============================================================
# CUSTOMER: MY BOOKINGS PAGE
# ============================================================
@app.route("/my-bookings")
def my_bookings():
    if session.get("role") != "Customer":
        return redirect("/login")

    from datetime import datetime, timedelta, time

    user_id = session["user_id"]
    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT tb.*, rt.table_number
        FROM table_bookings tb
        JOIN restaurant_tables rt ON tb.table_id = rt.table_id
        WHERE tb.customer_id=%s
        ORDER BY tb.booking_date DESC
    """, (user_id,))
    bookings = cursor.fetchall()
    cursor.close()

    now = datetime.now()
    for booking in bookings:
        booking_date = booking["booking_date"]
        booking_time = booking["booking_time"]
        if isinstance(booking_time, timedelta):
            seconds = booking_time.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            booking_time = time(hours, minutes)
        booking_datetime = datetime.combine(booking_date, booking_time)
        start_order_time = booking_datetime - timedelta(hours=1)
        cancel_limit = booking_datetime - timedelta(hours=6)
        booking["can_order"] = start_order_time <= now <= booking_datetime
        booking["can_cancel"] = now < cancel_limit and booking["booking_status"] == "Booked"

    return render_template("user/my_bookings.html", bookings=bookings)


# ============================================================
# CUSTOMER: USER INFO API (for sidebar)
# ============================================================
@app.route("/api/user-info")
def api_user_info():
    if session.get("role") != "Customer":
        return jsonify({}), 401
    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT name, phone, address FROM users WHERE user_id=%s", (session["user_id"],))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return jsonify(user)
    return jsonify({})


# ============================================================
# CUSTOMER: ORDER LOCATION API (for delivery tracking popup)
# ============================================================
@app.route("/api/order-location/<int:order_id>")
def api_order_location(order_id):
    if session.get("role") != "Customer":
        return jsonify({}), 401
    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT o.latitude, o.longitude,
               u.latitude AS rider_lat, u.longitude AS rider_lng
        FROM orders o
        LEFT JOIN users u ON u.user_id = o.delivery_id
        WHERE o.order_id=%s AND o.customer_id=%s
    """, (order_id, session["user_id"]))
    row = cursor.fetchone()
    cursor.close()
    if row:
        return jsonify({
            "lat": float(row["latitude"]) if row["latitude"] else None,
            "lng": float(row["longitude"]) if row["longitude"] else None,
            "rider_lat": float(row["rider_lat"]) if row.get("rider_lat") else None,
            "rider_lng": float(row["rider_lng"]) if row.get("rider_lng") else None,
        })
    return jsonify({})

@app.route("/get_order_details/<int:order_id>")
def get_order_details(order_id):

    if session.get("role") != "Customer":
        return jsonify({"error": "Unauthorized"}), 403

    conn = connect_db()
    cur = conn.cursor(MySQLdb.cursors.DictCursor)

    # 🔹 Get order date
    cur.execute("""
        SELECT order_date
        FROM orders
        WHERE order_id=%s
    """, (order_id,))
    order = cur.fetchone()

    # 🔹 Get items
    cur.execute("""
        SELECT oi.quantity,
               oi.price,
               m.item_name,
               m.image
        FROM order_items oi
        JOIN menu m ON oi.item_id = m.item_id
        WHERE oi.order_id=%s
    """, (order_id,))
    items = cur.fetchall()

    cur.close()

    return jsonify({
        "order_date": order["order_date"].strftime("%d %b %Y, %I:%M %p"),
        "items": items
    })


#CUSTOMEROVERHERE


# =========================================================
# SUPER ADMIN DASHBOARD
# =========================================================
@app.route("/super_admin_dashboard")
def super_admin_dashboard():

    if session.get("role") != "SuperAdmin":
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # =========================
    # USERS COUNT
    # =========================

    cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role='Employee'")
    total_employees = cursor.fetchone()["total"] or 0

    cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role='Manager'")
    total_managers = cursor.fetchone()["total"] or 0

    cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role='Customer'")
    total_customers = cursor.fetchone()["total"] or 0

    # =========================
    # TOTAL ORDERS (ALL TYPES)
    # =========================

    cursor.execute("SELECT COUNT(*) AS total FROM orders")
    total_orders = cursor.fetchone()["total"] or 0

    cursor.execute("SELECT COUNT(*) AS total FROM visitor_orders")
    total_orders += cursor.fetchone()["total"] or 0

    cursor.execute("SELECT COUNT(*) AS total FROM table_bookings")
    total_orders += cursor.fetchone()["total"] or 0

    # =========================
    # TOTAL REVENUE (ALL SOURCES)
    # =========================
    # ORDERS
    cursor.execute("""
        SELECT IFNULL(SUM(total_amount),0) AS total
        FROM orders
    """)
    orders_revenue = cursor.fetchone()["total"]

    # VISITOR
    cursor.execute("""
        SELECT IFNULL(SUM(final_amount),0) AS total
        FROM visitor_orders
    """)
    visitor_revenue = cursor.fetchone()["total"]

    # BOOKINGS
    cursor.execute("""
        SELECT IFNULL(SUM(total_price),0) AS total
        FROM table_bookings
    """)
    booking_revenue = cursor.fetchone()["total"]

    total_revenue = orders_revenue + visitor_revenue + booking_revenue

    # =========================
    # SALARIES
    # =========================

    cursor.execute("""
        SELECT IFNULL(SUM(amount + IFNULL(bonus,0)),0) AS total
        FROM salaries
        WHERE status='Paid'
    """)
    total_salary_paid = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT IFNULL(SUM(amount + IFNULL(bonus,0)),0) AS total
        FROM salaries
        WHERE status='Pending'
    """)
    total_salary_pending = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM salaries
        WHERE status='Paid'
    """)
    salary_paid_count = cursor.fetchone()["total"] or 0

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM salaries
        WHERE status='Pending'
    """)
    salary_pending_count = cursor.fetchone()["total"] or 0

    total_salary = total_salary_paid + total_salary_pending

    # =========================
    # MONTHLY REVENUE (ORDERS)
    # =========================

    cursor.execute("""
        SELECT MONTH(order_date) AS month,
               IFNULL(SUM(total_amount),0) AS total
        FROM orders
        WHERE payment_status='Paid'
        GROUP BY MONTH(order_date)
        ORDER BY MONTH(order_date)
    """)

    revenue_rows = cursor.fetchall()

    months = []
    monthly_income = []

    for row in revenue_rows:
        months.append(f"Month {row['month']}")
        monthly_income.append(float(row["total"]))

    # =========================
    # TODAY ORDERS (ALL TYPES)
    # =========================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE DATE(order_date)=CURDATE()
    """)
    today_orders = cursor.fetchone()["total"] or 0

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM visitor_orders
        WHERE DATE(order_time)=CURDATE()
    """)
    today_orders += cursor.fetchone()["total"] or 0

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM table_bookings
        WHERE booking_date=CURDATE()
    """)
    today_orders += cursor.fetchone()["total"] or 0

    # =========================
    # TODAY ORDER STATUS (ORDERS ONLY)
    # =========================

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE DATE(order_date)=CURDATE() AND status='Delivered'
    """)
    today_completed = cursor.fetchone()["total"] or 0

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE DATE(order_date)=CURDATE() AND status='Cooking'
    """)
    today_preparing = cursor.fetchone()["total"] or 0

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE DATE(order_date)=CURDATE() AND status='Cancelled'
    """)
    today_cancelled = cursor.fetchone()["total"] or 0

    # =========================
    # RECENT ORDERS
    # =========================

    cursor.execute("""
        SELECT 
            o.order_id,
            u.name AS customer_name,
            o.total_amount,
            o.status
        FROM orders o
        JOIN users u ON o.customer_id = u.user_id
        ORDER BY o.order_id DESC
        LIMIT 5
    """)

    recent_orders = cursor.fetchall()

    # =========================
    # TOP SELLING ITEMS (WITH FALLBACK)
    # =========================

    cursor.execute("""
        SELECT m.item_name AS name,
               SUM(oi.quantity) AS total_sold
        FROM order_items oi
        JOIN menu m ON m.item_id = oi.item_id
        GROUP BY oi.item_id
        ORDER BY total_sold DESC
        LIMIT 5
    """)

    top_items = cursor.fetchall()

    # Fallback if no data
    if not top_items:
        top_items = [
            {"name": "Paneer Butter Masala", "total_sold": 120},
            {"name": "Chicken Biryani", "total_sold": 95},
            {"name": "Veg Hakka Noodles", "total_sold": 80}
        ]

    cursor.close()

    return render_template(
        "admin/dashboard_a.html",

        total_employees=total_employees,
        total_managers=total_managers,
        total_customers=total_customers,

        total_orders=total_orders,
        total_income=total_revenue,

        total_salary_paid=total_salary_paid,
        total_salary_pending=total_salary_pending,
        total_salary=total_salary,

        salary_paid_count=salary_paid_count,
        salary_pending_count=salary_pending_count,

        months=months,
        monthly_income=monthly_income,

        today_orders=today_orders,
        today_completed=today_completed,
        today_preparing=today_preparing,
        today_cancelled=today_cancelled,

        recent_orders=recent_orders,
        top_items=top_items
    )
# =========================================================
# ADD STAFF
# =========================================================

@app.route("/super_admin/add-staff", methods=["GET", "POST"])
def add_staff():

    if session.get("role") != "SuperAdmin":
        return redirect("/login")

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")
        phone = request.form.get("phone")
        address = request.form.get("address")
        salary = request.form.get("salary")

        employee_type = request.form.get("employee_type")
        shift = request.form.get("shift")

        if role not in ["Manager", "Employee"]:
            return "Invalid Role"

        if not salary:
            salary = 0

        conn = connect_db()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)

        # check duplicate email
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            cursor.close()
            return "Email already exists"

        hashed_password = generate_password_hash(password)

        # insert into users
        cursor.execute("""
        INSERT INTO users
        (name,email,password,role,phone,address,salary,status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,'Active')
        """, (name,email,hashed_password,role,phone,address,salary))

        conn.commit()

        user_id = cursor.lastrowid

        # if employee insert extra data
        if role == "Employee":

            if not employee_type:
                employee_type = "Staff"

            if not shift:
                shift = "Morning"

            cursor.execute("""
            INSERT INTO employee_details
            (user_id, employee_type, shift, joining_date)
            VALUES (%s,%s,%s,CURDATE())
            """,(user_id,employee_type,shift))

            conn.commit()

        cursor.close()

        return redirect("/super_admin/manage-staff")

    return render_template("admin/add_staff.html")



# =========================================================
# MANAGE STAFF
# =========================================================
@app.route("/super_admin/manage-staff")
def manage_staff():

    if session.get("role") != "SuperAdmin":
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    search = request.args.get("search")
    no_result = False

    # ==============================
    # SEARCH STAFF
    # ==============================

    if search:

        cursor.execute("""
            SELECT u.*, e.employee_type, e.shift
            FROM users u
            LEFT JOIN employee_details e
            ON u.user_id = e.user_id
            WHERE u.role != 'Customer'
            AND (
                u.user_id LIKE %s
                OR u.name LIKE %s
                OR u.email LIKE %s
                OR u.phone LIKE %s
                OR u.role LIKE %s
            )
            ORDER BY u.user_id DESC
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))

        staff = cursor.fetchall()

    else:

        cursor.execute("""
            SELECT u.*, e.employee_type, e.shift
            FROM users u
            LEFT JOIN employee_details e
            ON u.user_id = e.user_id
            WHERE u.role != 'Customer'
            ORDER BY u.user_id DESC
        """)

        staff = cursor.fetchall()

    # ==============================
    # SALARY STATS
    # ==============================

    current_year = datetime.now().year
    current_month = datetime.now().month

    for user in staff:

        # Managers may not have salary tracking
        if user["role"] != "Employee":
            user["total_paid_months"] = 0
            user["pending_months"] = 0
            continue

        cursor.execute("""
            SELECT COUNT(*) AS total_paid
            FROM salaries
            WHERE user_id=%s
        """, (user["user_id"],))

        total_paid = cursor.fetchone()["total_paid"]

        cursor.execute("""
            SELECT MIN(year) AS start_year, MIN(month) AS start_month
            FROM salaries
            WHERE user_id=%s
        """, (user["user_id"],))

        start = cursor.fetchone()

        if start["start_year"] and start["start_month"]:
            months_worked = ((current_year - start["start_year"]) * 12) + \
                            (current_month - start["start_month"] + 1)
        else:
            months_worked = 0

        pending = months_worked - total_paid
        if pending < 0:
            pending = 0

        user["total_paid_months"] = total_paid
        user["pending_months"] = pending

    cursor.close()

    return render_template(
        "admin/manage_staff.html",
        staff=staff,
        no_result=no_result
    )
# =========================================================
# UPDATE STAFF
# =========================================================

# =========================================================
# UPDATE STAFF
# =========================================================

@app.route("/super_admin/update-staff/<int:user_id>", methods=["POST"])
def update_staff(user_id):

    if session.get("role") != "SuperAdmin":
        return redirect("/login")

    name = request.form.get("name","").strip()
    phone = request.form.get("phone","").strip()
    address = request.form.get("address","").strip()
    status = request.form.get("status","").strip()
    salary = request.form.get("salary","").strip()
    shift = request.form.get("shift","").strip()
    employee_type = request.form.get("employee_type","").strip()
    new_password = request.form.get("password","").strip()

    if not phone.isdigit() or len(phone) != 10:
        return "Phone number must be exactly 10 digits"

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT role FROM users WHERE user_id=%s",(user_id,))
    result = cursor.fetchone()

    if not result:
        cursor.close()
        return "User not found"

    staff_role = result["role"]

    if staff_role == "Employee":

        if salary == "":
            cursor.close()
            return "Salary is required"

        salary = float(salary)

        if new_password:
            hashed_password = generate_password_hash(new_password)

            cursor.execute("""
            UPDATE users
            SET name=%s, phone=%s, address=%s, status=%s, password=%s
            WHERE user_id=%s
            """, (name, phone, address, status, hashed_password, user_id))
        else:
            cursor.execute("""
                UPDATE users
                SET name=%s, phone=%s, address=%s, status=%s
                WHERE user_id=%s
            """,(name,phone,address,status,user_id))

        cursor.execute("""
            UPDATE employee_details
            SET employee_type=%s, shift=%s, salary=%s
            WHERE user_id=%s
        """,(employee_type,shift,salary,user_id))

    elif staff_role == "Manager":

        if new_password:
            hashed_password = generate_password_hash(new_password)  # ← FIXED

            cursor.execute("""
                UPDATE users
                SET name=%s, phone=%s, address=%s, status=%s, password=%s
                WHERE user_id=%s
            """,(name,phone,address,status,hashed_password,user_id))  # ← FIXED
        else:
            cursor.execute("""
                UPDATE users
                SET name=%s, phone=%s, address=%s, status=%s
                WHERE user_id=%s
            """,(name,phone,address,status,user_id))

    conn.commit()
    cursor.close()

    return redirect("/super_admin/manage-staff")

# =========================================================
# DELETE STAFF
# =========================================================

@app.route("/super_admin/delete-staff/<int:user_id>")
def delete_staff(user_id):

    if session.get("role") != "SuperAdmin":
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)



    cursor.execute("DELETE FROM users WHERE user_id=%s",(user_id,))
    conn.commit()

    cursor.close()

    return redirect("/super_admin/manage-staff")



# =========================================================
# PAY SALARY
# =========================================================
@app.route("/super_admin/pay-salary/<int:user_id>", methods=["POST"])
def pay_salary(user_id):

    if session.get("role") != "SuperAdmin":
        return redirect("/login")

    try:
        month = int(request.form.get("month"))
        year = int(request.form.get("year"))
    except:
        return "Invalid Month or Year"

    # BONUS SAFE HANDLE
    bonus = request.form.get("bonus")
    if not bonus or bonus.strip() == "":
        bonus = 0
    else:
        bonus = float(bonus)

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # GET FIXED SALARY
    cursor.execute("SELECT salary FROM users WHERE user_id=%s", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        return "User not found"

    fixed_salary = float(user["salary"])

    # CHECK IF ALREADY EXISTS
    cursor.execute("""
        SELECT salary_id FROM salaries
        WHERE user_id=%s AND month=%s AND year=%s
    """, (user_id, month, year))

    if cursor.fetchone():
        cursor.close()
        return "Salary already exists for this month"

    # ✅ INSERT CORRECT DATA
    cursor.execute("""
        INSERT INTO salaries (user_id, amount, bonus, month, year, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (user_id, fixed_salary, bonus, month, year, "Paid"))

    conn.commit()
    cursor.close()

    return redirect("/super_admin/manage-staff")

# =====================================================
# MANAGER DASHBOARD
# =====================================================
@app.route("/manager/dashboard")
def manager_dashboard():

    if session.get("role") != "Manager":
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # =========================
    # TOTAL ORDERS (ALL TYPES)
    # =========================
    cursor.execute("SELECT COUNT(*) AS total FROM orders")
    total_orders = cursor.fetchone()["total"] or 0

    cursor.execute("SELECT COUNT(*) AS total FROM visitor_orders")
    total_orders += cursor.fetchone()["total"] or 0

    cursor.execute("SELECT COUNT(*) AS total FROM table_bookings")
    total_orders += cursor.fetchone()["total"] or 0


    # =========================
    # TOTAL REVENUE (🔥 FIXED)
    # =========================

    # Orders revenue (ONLY PAID)
    cursor.execute("""
        SELECT IFNULL(SUM(total_amount),0) AS total
        FROM orders
        WHERE payment_status='Paid'
    """)
    orders_revenue = cursor.fetchone()["total"] or 0

    # Visitor orders (no payment_status → take all)
    cursor.execute("""
        SELECT IFNULL(SUM(final_amount),0) AS total
        FROM visitor_orders
    """)
    visitor_revenue = cursor.fetchone()["total"] or 0

    # Table bookings (ONLY PAID)
    cursor.execute("""
        SELECT IFNULL(SUM(total_price),0) AS total
        FROM table_bookings
        WHERE payment_status='Paid'
    """)
    booking_revenue = cursor.fetchone()["total"] or 0

    total_revenue = float(orders_revenue + visitor_revenue + booking_revenue)


    # =========================
    # EMPLOYEES
    # =========================
    cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role='Employee'")
    total_employees = cursor.fetchone()["total"] or 0


    # =========================
    # ORDER STATUS (ONLY ORDERS TABLE)
    # =========================
    cursor.execute("SELECT COUNT(*) AS total FROM orders WHERE status='Pending'")
    pending_orders = cursor.fetchone()["total"] or 0

    cursor.execute("""
        SELECT COUNT(*) AS total 
        FROM orders 
        WHERE status IN ('Delivered','Completed','Served')
    """)
    completed_orders = cursor.fetchone()["total"] or 0

    cursor.execute("SELECT COUNT(*) AS total FROM orders WHERE status='Cooking'")
    preparing_orders = cursor.fetchone()["total"] or 0

    cursor.execute("SELECT COUNT(*) AS total FROM orders WHERE status='Cancelled'")
    cancelled_orders = cursor.fetchone()["total"] or 0


    # =========================
    # TODAY ORDERS (ALL)
    # =========================
    cursor.execute("""
        SELECT COUNT(*) AS total FROM orders
        WHERE DATE(order_date)=CURDATE()
    """)
    today_orders = cursor.fetchone()["total"] or 0

    cursor.execute("""
        SELECT COUNT(*) AS total FROM visitor_orders
        WHERE DATE(order_time)=CURDATE()
    """)
    today_orders += cursor.fetchone()["total"] or 0

    cursor.execute("""
        SELECT COUNT(*) AS total FROM table_bookings
        WHERE booking_date=CURDATE()
    """)
    today_orders += cursor.fetchone()["total"] or 0


    # =========================
    # TODAY REVENUE (🔥 FIXED)
    # =========================

    cursor.execute("""
        SELECT IFNULL(SUM(total_amount),0) AS total
        FROM orders
        WHERE DATE(order_date)=CURDATE()
        AND payment_status='Paid'
    """)
    today_orders_rev = cursor.fetchone()["total"] or 0

    cursor.execute("""
        SELECT IFNULL(SUM(final_amount),0) AS total
        FROM visitor_orders
        WHERE DATE(order_time)=CURDATE()
    """)
    today_visitor_rev = cursor.fetchone()["total"] or 0

    cursor.execute("""
        SELECT IFNULL(SUM(total_price),0) AS total
        FROM table_bookings
        WHERE booking_date=CURDATE()
        AND payment_status='Paid'
    """)
    today_booking_rev = cursor.fetchone()["total"] or 0

    today_revenue = float(today_orders_rev + today_visitor_rev + today_booking_rev)


    # =========================
    # RECENT ORDERS (MERGED)
    # =========================
    cursor.execute("""
        SELECT order_id AS id, 'Order' AS type,
               total_amount AS total,
               status,
               order_date AS time
        FROM orders

        UNION ALL

        SELECT order_id AS id, 'Visitor' AS type,
               final_amount AS total,
               order_status AS status,
               order_time AS time
        FROM visitor_orders

        ORDER BY time DESC
        LIMIT 5
    """)
    recent_orders = cursor.fetchall()


    # =========================
    # REVENUE CHART (🔥 FIXED ALL SOURCES)
    # =========================
    cursor.execute("""
        SELECT DATE(date) AS dt, SUM(amount) AS total FROM (

            SELECT order_date AS date, total_amount AS amount
            FROM orders
            WHERE payment_status='Paid'

            UNION ALL

            SELECT order_time AS date, final_amount AS amount
            FROM visitor_orders

            UNION ALL

            SELECT booking_date AS date, total_price AS amount
            FROM table_bookings
            WHERE payment_status='Paid'

        ) AS combined

        WHERE date >= CURDATE() - INTERVAL 6 DAY
        GROUP BY DATE(date)
        ORDER BY DATE(date)
    """)

    chart_data = cursor.fetchall()

    revenue_labels = []
    revenue_data = []

    for row in chart_data:
        revenue_labels.append(row["dt"].strftime("%d %b"))
        revenue_data.append(float(row["total"]))


    cursor.close()

    return render_template(
        "manager/dashboard_m.html",

        total_orders=total_orders,
        total_revenue=total_revenue,
        total_employees=total_employees,

        pending_orders=pending_orders,
        completed_orders=completed_orders,
        preparing_orders=preparing_orders,
        cancelled_orders=cancelled_orders,

        today_orders=today_orders,
        today_revenue=today_revenue,

        recent_orders=recent_orders,

        revenue_labels=revenue_labels,
        revenue_data=revenue_data
    )

# =====================================================
# EMPLOYEE MANAGEMENT (MANAGER)
# =====================================================

@app.route("/manager/manage-employees")
def manager_manage_employees():

    if session.get("role") != "Manager":
        return redirect(url_for("login"))

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.*, e.employee_type, e.shift
        FROM users u
        LEFT JOIN employee_details e ON u.user_id = e.user_id
        WHERE u.role='Employee'
        ORDER BY u.user_id DESC
    """)

    employees = cursor.fetchall()
    cursor.close()

    return render_template("manager/manage_employees.html", employees=employees)


@app.route("/manager/add-employee", methods=["POST"])
def manager_add_employee():

    if session.get("role") != "Manager":
        return redirect(url_for("login"))

    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")
    phone = request.form.get("phone")
    address = request.form.get("address")
    salary = request.form.get("salary")

    if not name or not email or not password:
        return redirect(url_for("manager_manage_employees"))

    hashed_password = generate_password_hash(password)

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users
        (name,email,password,phone,address,salary,shift,employee_type,role,status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'Employee',%s)
    """, (name, email, hashed_password, phone, address, salary,
          request.form.get("shift"), request.form.get("employee_type"),
          request.form.get("status", "Active")))

    conn.commit()
    cursor.close()

    return redirect(url_for("manager_manage_employees"))


@app.route("/manager/update-employee/<int:user_id>", methods=["POST"])
def manager_update_employee(user_id):

    if session.get("role") != "Manager":
        return redirect(url_for("login"))

    conn = connect_db()
    cursor = conn.cursor()

    password = request.form.get("password")
    if password:
        from werkzeug.security import generate_password_hash
        cursor.execute("""
            UPDATE users SET name=%s,email=%s,phone=%s,address=%s,salary=%s,
            shift=%s,employee_type=%s,status=%s,password=%s
            WHERE user_id=%s AND role='Employee'
        """, (..., generate_password_hash(password), user_id))
    else:
        cursor.execute("""
            UPDATE users SET name=%s,email=%s,phone=%s,address=%s,salary=%s,
            shift=%s,employee_type=%s,status=%s
            WHERE user_id=%s AND role='Employee'
        """, (..., user_id))
    conn.commit()
    cursor.close()

    return redirect(url_for("manager_manage_employees"))


@app.route("/manager/delete-employee/<int:user_id>", methods=["POST"])
def manager_delete_employee(user_id):

    if session.get("role") != "Manager":
        return redirect(url_for("login"))

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM users
        WHERE user_id=%s
        AND role='Employee'
    """, (user_id,))

    conn.commit()
    cursor.close()

    return redirect(url_for("manager_manage_employees"))



# =====================================================
# CATEGORY MANAGEMENT (MANAGER / ADMIN)
# =====================================================

@app.route("/manager/categories")
def manager_categories():

    if session.get("role") not in ["Manager", "Admin"]:
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM categories ORDER BY category_id ASC")
    categories = cursor.fetchall()

    return render_template("manager/categories.html", categories=categories)


@app.route("/manager/add-category", methods=["POST"])
def add_category():

    if session.get("role") not in ["Manager", "Admin"]:
        return redirect("/login")

    category_name = request.form.get("category_name")

    if not category_name:
        return redirect("/manager/categories")

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO categories (category_name) VALUES (%s)",
        (category_name,)
    )

    conn.commit()

    return redirect("/manager/categories")


@app.route("/manager/delete-category/<int:category_id>")
def delete_category(category_id):

    if session.get("role") not in ["Manager", "Admin"]:
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM categories WHERE category_id=%s", (category_id,))
    conn.commit()

    return redirect("/manager/categories")

# =====================================================
# MENU MANAGEMENT (MANAGER / ADMIN)
# =====================================================

@app.route("/manager/menu", methods=["GET", "POST"])
def manager_menu():

    if session.get("role") not in ["Manager", "Admin"]:
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor()

    # -------------------------------------------------
    # ADD OR EDIT MENU ITEM
    # -------------------------------------------------
    if request.method == "POST":

        item_id = request.form.get("item_id")

        item_name = request.form.get("item_name")
        description = request.form.get("description")
        price = request.form.get("price")
        category_id = request.form.get("category_id")
        stock = request.form.get("stock")
        status = request.form.get("status")

        image_file = request.files.get("image")
        image_name = None

        # ---------- IMAGE UPLOAD ----------
        if image_file and image_file.filename != "":

            upload_folder = os.path.join("static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)

            ext = os.path.splitext(image_file.filename)[1]
            image_name = str(uuid.uuid4()) + ext

            image_path = os.path.join(upload_folder, image_name)
            image_file.save(image_path)

        # ---------- UPDATE MENU ITEM ----------
        if item_id:

            if image_name:
                cursor.execute("""
                    UPDATE menu SET
                        item_name=%s,
                        description=%s,
                        price=%s,
                        category_id=%s,
                        stock=%s,
                        status=%s,
                        image=%s
                    WHERE item_id=%s
                """, (
                    item_name, description, price,
                    category_id, stock, status,
                    image_name, item_id
                ))

            else:
                cursor.execute("""
                    UPDATE menu SET
                        item_name=%s,
                        description=%s,
                        price=%s,
                        category_id=%s,
                        stock=%s,
                        status=%s
                    WHERE item_id=%s
                """, (
                    item_name, description, price,
                    category_id, stock, status,
                    item_id
                ))

        # ---------- ADD NEW MENU ITEM ----------
        else:
            cursor.execute("""
                INSERT INTO menu
                (item_name, description, price, category_id, image, stock, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                item_name, description, price,
                category_id, image_name, stock, status
            ))

        conn.commit()


    # -------------------------------------------------
    # FETCH MENU ITEMS
    # -------------------------------------------------
    cursor.execute("""
        SELECT m.*, c.category_name
        FROM menu m
        LEFT JOIN categories c
        ON m.category_id = c.category_id
        ORDER BY m.item_id ASC
    """)
    menu_items = cursor.fetchall()

    # -------------------------------------------------
    # FETCH CATEGORIES
    # -------------------------------------------------
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    cursor.close()

    return render_template(
        "manager/menu.html",
        menu_items=menu_items,
        categories=categories
    )

# ======================================================
# MANAGER - MANAGE TABLES  (paste into app.py)
# photo column is VARCHAR(255) → stores filename
# files saved to: static/images/tables/
# ======================================================

TABLES_UPLOAD_FOLDER = os.path.join("static", "images", "tables")
ALLOWED_EXTENSIONS   = {"jpg", "jpeg", "png", "webp", "gif"}

def allowed_table_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── MANAGE TABLES PAGE ─────────────────────────────────

@app.route("/manager/manage-tables")
def manager_manage_tables():
    if session.get("role") != "Manager":
        return redirect("/login")

    conn   = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT table_id, table_number, capacity, price_per_person, photo
        FROM restaurant_tables
        ORDER BY table_number ASC
    """)
    tables = cursor.fetchall()
    cursor.close()

    return render_template(
        "manager/manage_tables.html",
        tables=tables,
        active_page="tables"
    )


# ── ADD TABLE ──────────────────────────────────────────

@app.route("/manager/add-table", methods=["POST"])
def manager_add_table():
    if session.get("role") != "Manager":
        return redirect("/login")

    table_number     = int(request.form.get("table_number"))
    capacity         = int(request.form.get("capacity"))
    price_per_person = float(request.form.get("price_per_person"))
    photo_file       = request.files.get("photo")

    conn   = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # Duplicate table number check
    cursor.execute(
        "SELECT table_id FROM restaurant_tables WHERE table_number=%s",
        (table_number,)
    )
    if cursor.fetchone():
        flash(f"Table #{table_number} already exists!", "danger")
        cursor.close()
        return redirect("/manager/manage-tables")

    # Save photo
    photo_filename = "default_table.jpg"
    if photo_file and photo_file.filename and allowed_table_file(photo_file.filename):
        ext            = photo_file.filename.rsplit(".", 1)[1].lower()
        photo_filename = f"table_{table_number}_{uuid.uuid4().hex[:8]}.{ext}"
        os.makedirs(TABLES_UPLOAD_FOLDER, exist_ok=True)
        photo_file.save(os.path.join(TABLES_UPLOAD_FOLDER, photo_filename))

    cursor.execute("""
        INSERT INTO restaurant_tables (table_number, capacity, price_per_person, photo)
        VALUES (%s, %s, %s, %s)
    """, (table_number, capacity, price_per_person, photo_filename))
    conn.commit()
    cursor.close()

    flash(f"Table #{table_number} added successfully!", "success")
    return redirect("/manager/manage-tables")


# ── EDIT TABLE ─────────────────────────────────────────

@app.route("/manager/edit-table", methods=["POST"])
def manager_edit_table():
    if session.get("role") != "Manager":
        return redirect("/login")

    table_id         = int(request.form.get("table_id"))
    table_number     = int(request.form.get("table_number"))
    capacity         = int(request.form.get("capacity"))
    price_per_person = float(request.form.get("price_per_person"))
    photo_file       = request.files.get("photo")

    conn   = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # Conflict check (another table already has this number)
    cursor.execute("""
        SELECT table_id FROM restaurant_tables
        WHERE table_number=%s AND table_id != %s
    """, (table_number, table_id))
    if cursor.fetchone():
        flash(f"Table #{table_number} already exists!", "danger")
        cursor.close()
        return redirect("/manager/manage-tables")

    if photo_file and photo_file.filename and allowed_table_file(photo_file.filename):
        # Delete old file if not the default
        cursor.execute(
            "SELECT photo FROM restaurant_tables WHERE table_id=%s", (table_id,)
        )
        old = cursor.fetchone()
        if old and old["photo"] and old["photo"] != "default_table.jpg":
            old_path = os.path.join(TABLES_UPLOAD_FOLDER, old["photo"])
            if os.path.exists(old_path):
                os.remove(old_path)

        ext            = photo_file.filename.rsplit(".", 1)[1].lower()
        photo_filename = f"table_{table_number}_{uuid.uuid4().hex[:8]}.{ext}"
        os.makedirs(TABLES_UPLOAD_FOLDER, exist_ok=True)
        photo_file.save(os.path.join(TABLES_UPLOAD_FOLDER, photo_filename))

        cursor.execute("""
            UPDATE restaurant_tables
            SET table_number=%s, capacity=%s, price_per_person=%s, photo=%s
            WHERE table_id=%s
        """, (table_number, capacity, price_per_person, photo_filename, table_id))
    else:
        cursor.execute("""
            UPDATE restaurant_tables
            SET table_number=%s, capacity=%s, price_per_person=%s
            WHERE table_id=%s
        """, (table_number, capacity, price_per_person, table_id))

    conn.commit()
    cursor.close()

    flash(f"Table #{table_number} updated successfully!", "success")
    return redirect("/manager/manage-tables")


# ── DELETE TABLE + RE-SORT NUMBERS ─────────────────────

@app.route("/manager/delete-table/<int:table_id>")
def manager_delete_table(table_id):
    if session.get("role") != "Manager":
        return redirect("/login")

    conn   = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute(
        "SELECT table_number, photo FROM restaurant_tables WHERE table_id=%s",
        (table_id,)
    )
    target = cursor.fetchone()

    if not target:
        flash("Table not found!", "danger")
        cursor.close()
        return redirect("/manager/manage-tables")

    deleted_number = target["table_number"]

    # Delete photo file from disk
    if target["photo"] and target["photo"] != "default_table.jpg":
        old_path = os.path.join(TABLES_UPLOAD_FOLDER, target["photo"])
        if os.path.exists(old_path):
            os.remove(old_path)

    cursor.execute("DELETE FROM restaurant_tables WHERE table_id=%s", (table_id,))
    conn.commit()

    # Re-sort: all tables with a higher number shift down by 1
    cursor.execute("""
        UPDATE restaurant_tables
        SET table_number = table_number - 1
        WHERE table_number > %s
        ORDER BY table_number ASC
    """, (deleted_number,))
    conn.commit()
    cursor.close()

    flash(f"Table #{deleted_number} deleted and numbers re-sorted!", "success")
    return redirect("/manager/manage-tables")

# ======================================================
# sidebar link — add to base_manager.html after Bookings:
#
# <a href="{{ url_for('manager_manage_tables') }}"
#    class="{% if active_page == 'tables' %}active{% endif %}">
#     Manage Tables
# </a>
# ======================================================
# =====================================================
# ORDER MANAGEMENT (MANAGER)
# =====================================================
# =====================================================
# MANAGER ORDERS DASHBOARD
# =====================================================
@app.route("/manager/orders")
def manager_orders():
    if session.get("role") != "Manager":
        return redirect("/login")

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 1️⃣ VISITOR MENU ORDERS
    cur.execute("""
        SELECT 
            order_id,
            customer_name,
            table_no,
            final_amount,
            order_status AS status,
            order_time AS order_date
        FROM visitor_orders
        WHERE order_status != 'Completed'
        ORDER BY order_time DESC
    """)
    visitor_orders = cur.fetchall()

    # 2️⃣ BOOKED TABLE ORDERS
    cur.execute("""
        SELECT 
            o.order_id,
            rt.table_number,
            o.total_amount,
            o.status,
            o.order_date
        FROM orders o
        JOIN restaurant_tables rt ON o.table_id = rt.table_id
        WHERE o.order_type='Table'
        AND o.status NOT IN ('Served','Cancelled')
        ORDER BY o.order_date DESC
    """)
    table_orders = cur.fetchall()

    # 3️⃣ ONLINE DELIVERY ORDERS
    cur.execute("""
        SELECT 
            order_id,
            total_amount,
            status,
            order_date
        FROM orders
        WHERE order_type='Online'
        AND status NOT IN ('Delivered','Cancelled')
        ORDER BY order_date DESC
    """)
    online_orders = cur.fetchall()

    cur.close()

    return render_template(
        "manager/orders.html",
        visitor_orders=visitor_orders,
        table_orders=table_orders,
        online_orders=online_orders
    )

# =====================================================
# GET ORDER DETAILS
# =====================================================
@app.route("/manager/order_details/<source>/<int:order_id>")
def manager_order_details(source, order_id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    order = None
    items = []

    try:
        if source == "visitor":
            cur.execute("SELECT * FROM visitor_orders WHERE order_id=%s", (order_id,))
            order = cur.fetchone()
            if not order:
                return jsonify({"error": "Order not found"}), 404

            cur.execute("""
                SELECT voi.quantity, voi.price, m.item_name
                FROM visitor_order_items voi
                JOIN menu m ON voi.menu_item_id = m.item_id
                WHERE voi.order_id=%s
            """, (order_id,))
            items = cur.fetchall()

        elif source in ["table", "online"]:
            cur.execute("SELECT * FROM orders WHERE order_id=%s", (order_id,))
            order = cur.fetchone()
            if not order:
                return jsonify({"error": "Order not found"}), 404

            cur.execute("""
                SELECT oi.quantity, oi.price, m.item_name
                FROM order_items oi
                JOIN menu m ON oi.item_id = m.item_id
                WHERE oi.order_id=%s
            """, (order_id,))
            items = cur.fetchall()
        else:
            return jsonify({"error": "Invalid order source"}), 400

    finally:
        cur.close()

    # Normalize status for frontend
    order["status"] = order.get("status") or order.get("order_status")

    return jsonify({"order": order, "items": items})

# =====================================================
# GET EMPLOYEES BY ROLE
# =====================================================
@app.route("/manager/get_employees/<role>")
def get_employees(role):
    if session.get("role") != "Manager":
        return jsonify({"error": "Unauthorized"}), 403

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    role_map = {
        "Cook": "Cook",
        "Waiter": "Waiter",
        "Delivery": "Delivery Boy"
    }

    employee_type = role_map.get(role)
    if not employee_type:
        return jsonify({"error": "Invalid role"}), 400

    cur.execute("""
        SELECT u.user_id, u.name, ed.employee_type
        FROM employee_details ed
        JOIN users u ON ed.user_id = u.user_id
        WHERE ed.employee_type=%s
    """, (employee_type,))

    employees = cur.fetchall()
    cur.close()

    return jsonify(employees)

# =====================================================
# ASSIGN EMPLOYEE TO ORDER
# =====================================================
@app.route("/manager/assign_employee", methods=["POST"])
def assign_employee():
    # -------------------- SESSION CHECK --------------------
    if session.get("role") != "Manager":
        return jsonify({"error": "Unauthorized"}), 403

    # -------------------- GET JSON DATA --------------------
    data = request.get_json()
    order_id = data.get("order_id")
    employee_id = data.get("employee_id")  # Must be users.user_id
    role = data.get("role")
    source = data.get("source")

    # -------------------- VALIDATE PARAMETERS --------------------
    if not all([order_id, employee_id, role, source]):
        return jsonify({"error": "Missing parameters"}), 400

    # -------------------- MAP ROLE TO COLUMN --------------------
    role_map = {
        "Cook": "cook_id",
        "Waiter": "waiter_id",
        "Delivery": "delivery_id"
    }
    column = role_map.get(role)
    if not column:
        return jsonify({"error": "Invalid role"}), 400

    # -------------------- MAP SOURCE TO TABLE --------------------
    table_map = {
        "visitor": "visitor_orders",
        "table": "orders",
        "online": "orders"
    }
    table = table_map.get(source)
    if not table:
        return jsonify({"error": "Invalid source"}), 400

    try:
        cur = mysql.connection.cursor()

        # -------------------- UPDATE EMPLOYEE IN ORDER --------------------
        # For 'orders' table: cook_id/waiter_id/delivery_id must reference users.user_id
        cur.execute(f"UPDATE {table} SET {column}=%s WHERE order_id=%s", (employee_id, order_id))
        mysql.connection.commit()
        cur.close()

        return jsonify({"status": "assigned"})

    except Exception as e:
        # Catch DB errors and return JSON instead of crashing
        return jsonify({"error": str(e)}), 500
# =====================================================
# UPDATE ORDER STATUS
# =====================================================
@app.route("/manager/update_order_status", methods=["POST"])
def update_order_status():
    if session.get("role") != "Manager":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    order_id = data.get("order_id")
    status = data.get("status")
    source = data.get("source")

    if not all([order_id, status, source]):
        return jsonify({"error": "Missing parameters"}), 400

    table_map = {"visitor": "visitor_orders", "table": "orders", "online": "orders"}
    column_map = {"visitor": "order_status", "table": "status", "online": "status"}

    table = table_map.get(source)
    column = column_map.get(source)
    if not table or not column:
        return jsonify({"error": "Invalid source"}), 400

    cur = mysql.connection.cursor()
    cur.execute(f"UPDATE {table} SET {column}=%s WHERE order_id=%s", (status, order_id))
    mysql.connection.commit()
    cur.close()

    return jsonify({"status": "updated"})

# =====================================================
# MANAGER: BOOKINGS PAGE
# =====================================================
@app.route("/manager/bookings")
def manager_bookings():
    if session.get("role") != "Manager":
        return redirect("/login")

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # ACTIVE BOOKINGS — booking datetime is in the future (or within last 2 hrs)
    cur.execute("""
        SELECT tb.booking_id,
               tb.booking_date,
               tb.booking_time,
               tb.table_id,
               tb.guests,
               tb.booking_status,
               tb.payment_status,
               rt.table_number,
               u.name,
               u.email,
               u.phone
        FROM table_bookings tb
        JOIN users u  ON tb.customer_id = u.user_id
        JOIN restaurant_tables rt ON tb.table_id = rt.table_id
        WHERE tb.booking_date IS NOT NULL
          AND tb.booking_time IS NOT NULL
          AND tb.booking_status != 'Cancelled'
          AND CONCAT(tb.booking_date, ' ', tb.booking_time)
              >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
        ORDER BY tb.booking_date ASC, tb.booking_time ASC
    """)
    active_bookings = cur.fetchall()
    cur.close()

    def _serialize(rows):
        result = []
        for row in rows:
            r = dict(row)
            if r.get("booking_date"):
                r["booking_date"] = str(r["booking_date"])
            if r.get("booking_time"):
                td = r["booking_time"]
                if hasattr(td, "seconds"):
                    total_sec = int(td.total_seconds())
                    h, rem = divmod(total_sec, 3600)
                    m = rem // 60
                    r["booking_time"] = f"{h:02d}:{m:02d}"
                else:
                    r["booking_time"] = str(td)
            if r.get("total_price") is not None:
                r["total_price"] = float(r["total_price"])
            result.append(r)
        return result

    return render_template(
        "manager/bookings.html",
        active_bookings=_serialize(active_bookings),
        active_page="bookings"
    )


# =====================================================
# MANAGER: BOOKING DETAILS (modal fetch)
# =====================================================
@app.route("/manager/booking_details/<int:booking_id>")
def booking_details(booking_id):
    if session.get("role") != "Manager":
        return jsonify({"error": "Unauthorized"}), 403

    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("""
            SELECT tb.booking_id,
                   tb.booking_date,
                   tb.booking_time,
                   tb.guests,
                   tb.booking_status,
                   tb.payment_status,
                   tb.total_price,
                   rt.table_number,
                   u.name,
                   u.email,
                   u.phone,
                   u.address
            FROM table_bookings tb
            JOIN users u  ON tb.customer_id = u.user_id
            JOIN restaurant_tables rt ON tb.table_id = rt.table_id
            WHERE tb.booking_id = %s
        """, (booking_id,))
        booking = cur.fetchone()

        if not booking:
            cur.close()
            return jsonify({"error": "Booking not found"}), 404

        cur.execute("""
            SELECT m.item_name,
                   SUM(oi.quantity) AS quantity,
                   oi.price
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.order_id
            JOIN menu m          ON m.item_id   = oi.item_id
            WHERE o.table_id = (
                    SELECT table_id FROM table_bookings WHERE booking_id = %s
                  )
              AND o.customer_id = (
                    SELECT customer_id FROM table_bookings WHERE booking_id = %s
                  )
              AND o.order_type = 'Table'
              AND o.status NOT IN ('Cancelled')
            GROUP BY m.item_name, oi.price
        """, (booking_id, booking_id))
        items = cur.fetchall()
        cur.close()

    except Exception as e:
        app.logger.error(f"booking_details DB error: {e}")
        return jsonify({"error": "Database error: " + str(e)}), 500

    # Serialize — safe against NULL values
    if booking.get("booking_date"):
        booking["booking_date"] = str(booking["booking_date"])
    else:
        booking["booking_date"] = "—"

    if booking.get("booking_time") is not None:
        td = booking["booking_time"]
        try:
            if hasattr(td, "total_seconds"):
                total_sec = int(td.total_seconds())
                h, rem = divmod(total_sec, 3600)
                m = rem // 60
                booking["booking_time"] = f"{h:02d}:{m:02d}"
            else:
                booking["booking_time"] = str(td)
        except Exception:
            booking["booking_time"] = str(td)
    else:
        booking["booking_time"] = "—"

    booking["total_price"] = float(booking["total_price"]) if booking.get("total_price") is not None else 0.0
    booking["payment_status"] = booking.get("payment_status") or "—"

    serialized_items = [
        {
            "item_name": i["item_name"],
            "quantity":  int(i["quantity"]),
            "price":     float(i["price"]),
        }
        for i in items
    ]
    order_total = sum(i["price"] * i["quantity"] for i in serialized_items)

    return jsonify({
        "booking": booking,
        "items":   serialized_items,
        "total":   order_total,
    })


# =====================================================
# MANAGER: TODAY'S BOOKINGS
# =====================================================
@app.route("/manager/todays_bookings")
def todays_bookings():
    if session.get("role") != "Manager":
        return jsonify({"error": "Unauthorized"}), 403

    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("""
            SELECT tb.booking_id,
                   tb.booking_time,
                   tb.guests,
                   tb.booking_status,
                   rt.table_number,
                   u.name
            FROM table_bookings tb
            JOIN users u  ON tb.customer_id = u.user_id
            JOIN restaurant_tables rt ON tb.table_id = rt.table_id
            WHERE tb.booking_date = CURDATE()
              AND tb.booking_status != 'Cancelled'
            ORDER BY tb.booking_time ASC
        """)
        bookings = cur.fetchall()
        cur.close()
    except Exception as e:
        app.logger.error(f"todays_bookings DB error: {e}")
        return jsonify({"error": "Database error: " + str(e)}), 500

    for b in bookings:
        if b.get("booking_time") is not None:
            td = b["booking_time"]
            try:
                if hasattr(td, "total_seconds"):
                    total_sec = int(td.total_seconds())
                    h, rem = divmod(total_sec, 3600)
                    m = rem // 60
                    b["booking_time"] = f"{h:02d}:{m:02d}"
                else:
                    b["booking_time"] = str(td)
            except Exception:
                b["booking_time"] = str(td)
        else:
            b["booking_time"] = "—"

    return jsonify(bookings)


# =====================================================
# MANAGER: HISTORY BOOKINGS
# =====================================================
@app.route("/manager/history_bookings")
def history_bookings_api():
    if session.get("role") != "Manager":
        return jsonify({"error": "Unauthorized"}), 403

    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("""
            SELECT tb.booking_id,
                   tb.booking_date,
                   tb.booking_time,
                   tb.guests,
                   tb.booking_status,
                   rt.table_number,
                   u.name,
                   u.email,
                   u.phone
            FROM table_bookings tb
            JOIN users u  ON tb.customer_id = u.user_id
            JOIN restaurant_tables rt ON tb.table_id = rt.table_id
            WHERE tb.booking_date IS NOT NULL
              AND tb.booking_time IS NOT NULL
              AND (
                    tb.booking_status = 'Cancelled'
                    OR CONCAT(tb.booking_date, ' ', tb.booking_time)
                       < DATE_SUB(NOW(), INTERVAL 2 HOUR)
                  )
            ORDER BY tb.booking_date DESC, tb.booking_time DESC
            LIMIT 100
        """)
        bookings = cur.fetchall()
        cur.close()
    except Exception as e:
        app.logger.error(f"history_bookings DB error: {e}")
        return jsonify({"error": "Database error: " + str(e)}), 500

    for b in bookings:
        if b.get("booking_date"):
            b["booking_date"] = str(b["booking_date"])
        if b.get("booking_time") is not None:
            td = b["booking_time"]
            try:
                if hasattr(td, "total_seconds"):
                    total_sec = int(td.total_seconds())
                    h, rem = divmod(total_sec, 3600)
                    m = rem // 60
                    b["booking_time"] = f"{h:02d}:{m:02d}"
                else:
                    b["booking_time"] = str(td)
            except Exception:
                b["booking_time"] = str(td)
        else:
            b["booking_time"] = "—"

    return jsonify(bookings)
# =====================================================
# MANAGER: CANCEL BOOKING
# =====================================================
@app.route("/manager/cancel_booking", methods=["POST"])
def manager_cancel_booking():
    if session.get("role") != "Manager":
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    data = request.get_json()
    booking_id = data.get("booking_id")

    if not booking_id:
        return jsonify({"status": "error", "message": "Missing booking ID"}), 400

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE table_bookings
        SET booking_status = 'Cancelled'
        WHERE booking_id = %s
    """, (booking_id,))
    mysql.connection.commit()
    affected = cur.rowcount
    cur.close()

    if affected:
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Booking not found"}), 404


# ============================================================
# EMPLOYEE DASHBOARD ROUTER
# ============================================================
@app.route("/employee/dashboard")
def employee_dashboard():

    if session.get("role") != "Employee":
        return redirect("/login")

    employee_type = session.get("employee_type")

    if employee_type == "Cook":
        return redirect("/cook/dashboard")

    elif employee_type == "Delivery Boy":
        return redirect("/delivery/dashboard")

    elif employee_type == "Waiter":
        return redirect("/waiter/dashboard")

    return redirect("/login")
# ============================================================
# COOK DASHBOARD
# ============================================================
@app.route("/cook/dashboard")
def cook_dashboard():

    if session.get("role") != "Employee" or session.get("employee_type") != "Cook":
        return redirect("/login")

    employee_id = session.get("user_id")

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # ---------------- Employee Info ----------------
    cursor.execute("""
        SELECT u.name, e.shift
        FROM users u
        LEFT JOIN employee_details e
        ON u.user_id = e.user_id
        WHERE u.user_id=%s
    """, (employee_id,))

    employee = cursor.fetchone()

    current_shift = employee["shift"] if employee else "Not Assigned"
    station = "Main Kitchen"
    head_chef = "Chef Arjun"

    # ---------------- Pending (Unassigned) ----------------
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE status='Pending'
        AND cook_id IS NULL
    """)
    pending_orders = cursor.fetchone()["total"]

    # ---------------- Cooking (My Orders) ----------------
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE status='Cooking'
        AND cook_id = %s
    """, (employee_id,))
    cooking_orders = cursor.fetchone()["total"]

    # ---------------- Ready (My Orders) ----------------
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE status='Ready'
        AND cook_id = %s
    """, (employee_id,))
    ready_orders = cursor.fetchone()["total"]

    # ---------------- Completed Today (My Orders) ----------------
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE status='Delivered'
        AND cook_id = %s
        AND DATE(order_date)=CURDATE()
    """, (employee_id,))
    completed_today = cursor.fetchone()["total"]

    # ---------------- Today's Specials ----------------
    cursor.execute("""
        SELECT item_name
        FROM menu
        ORDER BY RAND()
        LIMIT 3
    """)
    specials = [row["item_name"] for row in cursor.fetchall()]

    # ---------------- Kitchen Activity ----------------
    cursor.execute("""
        SELECT o.order_id, m.item_name
        FROM orders o
        JOIN order_items oi ON oi.order_id=o.order_id
        JOIN menu m ON m.item_id=oi.item_id
        ORDER BY o.order_id DESC
        LIMIT 5
    """)

    activity_feed = [
        f"Order #{row['order_id']} - {row['item_name']} started cooking"
        for row in cursor.fetchall()
    ]

    cursor.close()

    return render_template(
        "employee/cook_dashboard.html",
        pending_orders=pending_orders,
        cooking_orders=cooking_orders,
        ready_orders=ready_orders,
        completed_today=completed_today,
        current_shift=current_shift,
        station=station,
        head_chef=head_chef,
        specials=specials,
        activity_feed=activity_feed
    )
    # ============================================================
    # DELIVERY DASHBOARD
    # ============================================================
# ============================================================
# DELIVERY DASHBOARD
# ============================================================
@app.route("/delivery/dashboard")
def delivery_dashboard():

    if session.get("role") != "Employee" or session.get("employee_type") != "Delivery Boy":
        return redirect("/login")

    employee_id = session.get("user_id")

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # ---------------- Delivery Orders ----------------
    cursor.execute("""
        SELECT o.order_id,
               o.order_date,
               o.status,
               u.name AS customer_name,
               u.address AS delivery_address,
               u.phone
        FROM orders o
        JOIN users u ON u.user_id = o.customer_id
        WHERE o.status IN ('Ready','Picked')
        ORDER BY o.order_id DESC
    """)

    deliveries = cursor.fetchall()

    # Fetch items for each order
    for order in deliveries:
        cursor.execute("""
            SELECT m.item_name, oi.quantity
            FROM order_items oi
            JOIN menu m ON m.item_id = oi.item_id
            WHERE oi.order_id = %s
        """, (order["order_id"],))

        order["items"] = cursor.fetchall()

    # ---------------- Dashboard Stats ----------------
    cursor.execute("SELECT COUNT(*) AS total FROM orders WHERE status='Ready'")
    pending_orders = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM orders WHERE status='Picked'")
    picked_orders = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE status='Delivered'
        AND DATE(order_date)=CURDATE()
    """)
    delivered_today = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM orders
        WHERE DATE(order_date)=CURDATE()
    """)
    total_orders_today = cursor.fetchone()["total"]

    # ---------------- Notifications ----------------
    cursor.execute("""
        SELECT message,
        DATE_FORMAT(created_at,'%%H:%%i') AS time
        FROM notifications
        WHERE employee_id=%s
        ORDER BY created_at DESC
        LIMIT 5
    """, (employee_id,))

    notifications = cursor.fetchall()

    cursor.close()

    deliveries_json = json.dumps([
        {
            "order_id": d["order_id"],
            "customer_name": d["customer_name"],
            "address": d["delivery_address"]
        }
        for d in deliveries
    ])

    return render_template(
        "employee/delivery_dashboard.html",
        deliveries=deliveries,
        pending_orders=pending_orders,
        picked_orders=picked_orders,
        delivered_today=delivered_today,
        total_orders_today=total_orders_today,
        notifications=notifications,
        deliveries_json=deliveries_json  # ✅ USE THIS (NOT json.dumps(deliveries))
    )
# Mark order as Picked-===============================
@app.route("/delivery/mark-picked/<int:order_id>", methods=["POST"])
def mark_picked(order_id):
    if session.get("role") != "Employee" or session.get("employee_type") != "Delivery Boy":
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status='Picked' WHERE order_id=%s", (order_id,))
    conn.commit()
    cursor.close()
    return redirect("/delivery/dashboard")

# Mark order as Delivered
@app.route("/delivery/mark-delivered/<int:order_id>", methods=["POST"])
def mark_delivered(order_id):
    if session.get("role") != "Employee" or session.get("employee_type") != "Delivery Boy":
        return redirect("/login")

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status='Delivered' WHERE order_id=%s", (order_id,))
    conn.commit()
    cursor.close()
    return redirect("/delivery/dashboard")

# Update availability status
@app.route("/delivery/set-status/<status>", methods=["POST"])
def set_status(status):
    if session.get("role") != "Employee" or session.get("employee_type") != "Delivery Boy":
        return redirect("/login")

    if status not in ["Available", "Unavailable"]:
        return "Invalid status"

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET sub_role=%s WHERE user_id=%s", (status, session.get("user_id")))
    conn.commit()
    cursor.close()
    session["sub_role"] = status
    return redirect("/delivery/dashboard")

# Report Issue
@app.route("/delivery/report-issue", methods=["POST"])
def report_issue():
    if session.get("role") != "Employee" or session.get("employee_type") != "Delivery Boy":
        return redirect("/login")

    order_id = request.form.get("order_id")
    message = request.form.get("message")

    if not order_id or not message:
        flash("Please provide order ID and issue details")
        return redirect("/delivery/dashboard")

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO delivery_alerts (employee_id, message)
        VALUES (%s, %s)
    """, (session.get("user_id"), f"Order #{order_id} Issue: {message}"))
    conn.commit()
    cursor.close()

    flash("Issue reported successfully")
    return redirect("/delivery/dashboard")

# ============================================================
# WAITER DASHBOARD
# ============================================================
@app.route("/waiter/dashboard")
def waiter_dashboard():

    if session.get("role") != "Employee" or session.get("employee_type") != "Waiter":
        return redirect("/login")

    waiter_id = session.get("user_id")

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT 
            tb.booking_id,
            tb.table_id,
            tb.guests,
            tb.booking_date,
            tb.booking_time,
            tb.booking_status,
            u.name AS customer_name
        FROM table_bookings tb
        JOIN users u ON tb.customer_id = u.user_id
        WHERE tb.waiter_id = %s
        ORDER BY tb.booking_date DESC
    """, (waiter_id,))

    tables = cursor.fetchall()

    cursor.close()

    return render_template(
        "employee/waiter_dashboard.html",
        tables=tables
    )
# ============================================================
# EMPLOYEE PROFILE (VIEW + EDIT)
# ============================================================

@app.route("/employee/profile", methods=["GET", "POST"])
def employee_profile():

    if session.get("role") != "Employee":
        return redirect("/login")

    user_id = session["user_id"]

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # ---------------- UPDATE PROFILE ----------------
    if request.method == "POST":

        name = request.form.get("name")
        phone = request.form.get("phone")

        photo = request.files.get("photo")

        if photo and photo.filename != "":
            photo_data = photo.read()

            cursor.execute("""
                UPDATE users
                SET name=%s, phone=%s, photo=%s
                WHERE user_id=%s
            """, (name, phone, photo_data, user_id))

        else:
            cursor.execute("""
                UPDATE users
                SET name=%s, phone=%s
                WHERE user_id=%s
            """, (name, phone, user_id))

        conn.commit()

    # ---------------- FETCH EMPLOYEE DATA ----------------
    cursor.execute("""
        SELECT user_id, name, email, phone, photo
        FROM users
        WHERE user_id=%s
    """, (user_id,))

    employee = cursor.fetchone()

    cursor.close()

    return render_template(
        "employee/edit_profile.html",
        employee=employee
    )

@app.route("/employee/photo/<int:user_id>")
def employee_photo(user_id):

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT photo FROM users WHERE user_id=%s", (user_id,))
    user = cursor.fetchone()

    cursor.close()

    if user and user["photo"]:
        return Response(user["photo"], mimetype="image/jpeg")

    # Show default image if no photo
    return send_file("static/images/defaultprof.png", mimetype="image/png")
#=================================================


@app.route("/employee/assigned-orders")
def employee_assigned_orders():

    if session.get("role") != "Employee":
        return redirect("/login")

    employee_type = session.get("employee_type")

    if employee_type == "Cook":
        return redirect("/cook/assigned-orders")

    elif employee_type == "Delivery Boy":
        return redirect("/delivery/assigned-orders")

    elif employee_type == "Waiter":
        return redirect("/waiter/assigned-orders")

    return redirect("/employee/dashboard")

@app.route("/waiter/assigned-orders")
def waiter_assigned_orders():

    if session.get("role") != "Employee" or session.get("employee_type") != "Waiter":
        return redirect("/login")

    waiter_id = session["user_id"]

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT 
            o.order_id,
            o.table_id,
            o.status,
            o.order_date,
            u.name AS customer_name
        FROM orders o
        JOIN users u ON o.customer_id = u.user_id
        WHERE o.waiter_id=%s
        AND o.order_type='Table'
        ORDER BY o.order_date DESC
    """,(waiter_id,))

    orders = cursor.fetchall()

    cursor.close()

    return render_template(
        "employee/waiter_assigned_orders.html",
        orders=orders
    )

@app.route("/cook/assigned-orders")
def cook_assigned_orders():

    if session.get("role") != "Employee" or session.get("employee_type") != "Cook":
        return redirect("/login")

    cook_id = session.get("user_id")

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT 
            o.order_id,
            o.order_type,
            o.table_id,
            o.status,
            o.order_date,
            u.name AS customer_name
        FROM orders o
        JOIN users u ON o.customer_id = u.user_id
        WHERE o.cook_id=%s
        ORDER BY o.order_date DESC
    """, (cook_id,))

    orders = cursor.fetchall()

    cursor.close()

    return render_template(
        "employee/cook_assigned_orders.html",
        orders=orders
    )
@app.route("/delivery/assigned-orders")
def delivery_assigned_orders():

    if session.get("role") != "Employee" or session.get("employee_type") != "Delivery Boy":
        return redirect("/login")

    delivery_id = session["user_id"]

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT 
            o.order_id,
            o.latitude,
            o.longitude,
            o.status,
            o.order_date,
            u.name AS customer_name,
            u.phone
        FROM orders o
        JOIN users u ON o.customer_id = u.user_id
        WHERE o.delivery_id=%s
        AND o.status IN ('Ready','Delivering')
        ORDER BY o.order_date DESC
    """, (delivery_id,))

    orders = cursor.fetchall()
    cursor.close()

    return render_template(
        "employee/delivery_assigned_orders.html",
        orders=orders
    )
@app.route('/start_delivery', methods=['POST'])
def start_delivery():

    if session.get("employee_type") != "Delivery Boy":
        return redirect("/login")

    import random
    delivery_id = session["user_id"]
    order_id = request.form['order_id']
    otp = str(random.randint(1000, 9999))  # string so no leading-zero loss

    conn = connect_db()
    cursor = conn.cursor()

    # ✅ Generate OTP once here when delivery starts — never gets overwritten again
    cursor.execute("""
        UPDATE orders 
        SET status='Delivering', delivery_otp=%s
        WHERE order_id=%s AND delivery_id=%s AND delivery_otp IS NULL
    """, (otp, order_id, delivery_id))

    conn.commit()
    cursor.close()

    return redirect('/delivery/assigned-orders')

import random
from flask import jsonify

@app.route('/generate_otp', methods=['POST'])
def generate_otp():

    delivery_id = session["user_id"]
    order_id = request.form['order_id']

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # ✅ Only set OTP if one doesn't already exist — never overwrite
    cursor.execute("""
        SELECT delivery_otp FROM orders
        WHERE order_id=%s AND delivery_id=%s
    """, (order_id, delivery_id))
    row = cursor.fetchone()

    if not row or not row['delivery_otp']:
        otp = str(random.randint(1000, 9999))  # string so no leading-zero loss
        cursor.execute("""
            UPDATE orders SET delivery_otp=%s
            WHERE order_id=%s AND delivery_id=%s
        """, (otp, order_id, delivery_id))
        conn.commit()

    cursor.close()
    return jsonify({"message": "OTP ready"})

@app.route('/verify_otp', methods=['POST'])
def verify_otp():

    order_id = request.form['order_id']
    entered_otp = request.form['otp'].strip()

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # ✅ Query ONLY by order_id — no session/delivery_id dependency that could silently fail
    cursor.execute("""
        SELECT delivery_otp 
        FROM orders 
        WHERE order_id=%s
    """, (order_id,))

    result = cursor.fetchone()

    db_otp = str(int(result['delivery_otp'])).strip() if result and result['delivery_otp'] is not None else None
    # int() first removes any decimal point if MySQL returns it as Decimal/float

    if db_otp and db_otp == entered_otp:

        cursor.execute("""
            UPDATE orders 
            SET status='Delivered', delivery_otp=NULL
            WHERE order_id=%s
        """, (order_id,))

        conn.commit()
        cursor.close()

        return jsonify({"success": True, "message": "✅ Order Delivered Successfully"})
    else:
        cursor.close()
        return jsonify({"success": False, "message": "❌ Invalid OTP"})

# ============================================================
# DELIVERY BOY: UPDATE RIDER LOCATION (Continuous GPS)
# ============================================================
@app.route("/api/update-rider-location", methods=["POST"])
def update_rider_location():
    if session.get("role") != "Employee" or session.get("employee_type") != "Delivery Boy":
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    lat = data.get("lat")
    lng = data.get("lng")

    if lat is None or lng is None:
        return jsonify({"error": "Missing lat/lng"}), 400

    conn = connect_db()
    cursor = conn.cursor()
    # Update rider's coordinates in users table
    cursor.execute("""
        UPDATE users SET latitude=%s, longitude=%s WHERE user_id=%s
    """, (lat, lng, session["user_id"]))
    conn.commit()
    cursor.close()

    return jsonify({"status": "ok"})


# ============================================================
# DELIVERY BOY: GET RIDER LOCATION (for customer tracking)
# ============================================================
@app.route("/api/rider-location/<int:order_id>")
def api_rider_location(order_id):
    if session.get("role") != "Customer":
        return jsonify({}), 401

    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT u.latitude AS lat, u.longitude AS lng
        FROM orders o
        JOIN users u ON u.user_id = o.delivery_id
        WHERE o.order_id=%s AND o.customer_id=%s AND o.status='Delivering'
    """, (order_id, session["user_id"]))
    row = cursor.fetchone()
    cursor.close()

    if row and row["lat"] and row["lng"]:
        return jsonify({"lat": float(row["lat"]), "lng": float(row["lng"])})
    return jsonify({})


# ============================================================
# COOK: LIVE ORDERS API (for cook dashboard)
# ============================================================
@app.route("/api/cook/live-orders")
def api_cook_live_orders():
    emp_type = (session.get("employee_type") or "").strip().lower()
    if session.get("role") != "Employee" or emp_type != "cook":
        return jsonify([]), 401

    cook_id = session["user_id"]
    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT o.order_id, o.order_type, o.table_id, o.status,
               o.total_amount, o.order_date,
               u.name AS customer_name
        FROM orders o
        JOIN users u ON o.customer_id = u.user_id
        WHERE o.cook_id=%s AND o.status IN ('Pending','Cooking','Ready')
        ORDER BY o.order_date ASC
    """, (cook_id,))
    orders = cursor.fetchall()

    result = []
    for order in orders:
        # Get items summary
        cursor.execute("""
            SELECT m.item_name, oi.quantity
            FROM order_items oi JOIN menu m ON m.item_id = oi.item_id
            WHERE oi.order_id=%s LIMIT 3
        """, (order["order_id"],))
        items = cursor.fetchall()
        items_summary = ", ".join([f"{i['item_name']} ×{i['quantity']}" for i in items])

        order_dict = dict(order)
        order_dict["items_summary"] = items_summary
        # Convert non-serializable types
        if order_dict.get("order_date"):
            order_dict["order_date"] = str(order_dict["order_date"])
        if order_dict.get("total_amount"):
            order_dict["total_amount"] = float(order_dict["total_amount"])
        result.append(order_dict)

    cursor.close()
    return jsonify(result)


# ============================================================
# COOK: UPDATE ORDER STATUS (Pending → Preparing → Ready)
# ============================================================
@app.route("/api/cook/update-status", methods=["POST"])
def api_cook_update_status():
    emp_type = (session.get("employee_type") or "").strip().lower()
    if session.get("role") != "Employee" or emp_type != "cook":
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    order_id = data.get("order_id")
    new_status = data.get("status")

    # Only allow valid transitions
    valid_statuses = ["Cooking", "Ready"]
    if new_status not in valid_statuses:
        return jsonify({"error": "Invalid status"}), 400

    cook_id = session["user_id"]
    conn = connect_db()
    cursor = conn.cursor()

    # Verify cook owns this order
    cursor.execute("""
        UPDATE orders SET status=%s
        WHERE order_id=%s AND cook_id=%s
    """, (new_status, order_id, cook_id))

    conn.commit()
    affected = cursor.rowcount
    cursor.close()

    if affected:
        return jsonify({"status": "ok"})
    return jsonify({"error": "Order not found or not assigned to you"}), 404

# ============================================================
# ADD THIS ROUTE TO app.py (before the final if __name__ block)
# Waiter: Live table orders API (for waiter dashboard live update)
# ============================================================

@app.route("/api/waiter/live-orders")
def api_waiter_live_orders():
    emp_type = (session.get("employee_type") or "").strip().lower()
    if session.get("role") != "Employee" or emp_type != "waiter":
        return jsonify([]), 401

    waiter_id = session["user_id"]
    conn = connect_db()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT o.order_id, o.table_id, o.status,
               o.total_amount, o.order_date,
               u.name AS customer_name
        FROM orders o
        JOIN users u ON o.customer_id = u.user_id
        WHERE o.waiter_id = %s
          AND o.order_type = 'Table'
          AND o.status IN ('Pending', 'Cooking', 'Ready', 'Served', 'Completed')
        ORDER BY o.order_date DESC
        LIMIT 20
    """, (waiter_id,))
    orders = cursor.fetchall()

    result = []
    for order in orders:
        cursor.execute("""
            SELECT m.item_name, oi.quantity
            FROM order_items oi
            JOIN menu m ON m.item_id = oi.item_id
            WHERE oi.order_id = %s
            LIMIT 3
        """, (order["order_id"],))
        items = cursor.fetchall()
        items_summary = ", ".join([f"{i['item_name']} ×{i['quantity']}" for i in items])

        d = dict(order)
        d["items_summary"] = items_summary
        if d.get("order_date"):
            d["order_date"] = str(d["order_date"])
        if d.get("total_amount"):
            d["total_amount"] = float(d["total_amount"])
        result.append(d)

    cursor.close()
    return jsonify(result)

# ============================================================
# WAITER: UPDATE BOOKING/ORDER STATUS
# ============================================================
@app.route("/api/waiter/update-status", methods=["POST"])
def api_waiter_update_status():
    # Case-insensitive role check to handle DB inconsistencies
    emp_type = (session.get("employee_type") or "").strip().lower()
    if session.get("role") != "Employee" or emp_type != "waiter":
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    order_id = data.get("order_id")
    new_status = data.get("status")

    valid_statuses = ["Served", "Completed"]
    if new_status not in valid_statuses:
        return jsonify({"error": "Invalid status"}), 400

    if not order_id:
        return jsonify({"error": "Missing order_id"}), 400

    waiter_id = session["user_id"]
    conn = connect_db()
    cursor = conn.cursor()

    # Removed AND waiter_id=%s — waiter_id may be NULL if assignment didn't set it
    # Also stamps waiter_id now so future queries work correctly
    cursor.execute("""
        UPDATE orders SET status=%s, waiter_id=%s
        WHERE order_id=%s AND order_type='Table'
    """, (new_status, waiter_id, order_id))

    conn.commit()
    affected = cursor.rowcount
    cursor.close()

    if affected == 0:
        return jsonify({"error": f"Order #{order_id} not found or not a table order"}), 404

    return jsonify({"status": "ok"})


#============================================

# ==============================
# LOGOUT
# ==============================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ==============================
# RUN
# ==============================
if __name__ == "__main__":
    app.run(debug=True)