from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'foodnshop_secret_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///foodnshop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ===================== MODELS =====================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    business_name = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'shop' or 'restaurant'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StockItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0)
    unit = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0)
    min_stock = db.Column(db.Float, default=5)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    is_available = db.Column(db.Boolean, default=True)

class Table(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    table_number = db.Column(db.String(20), nullable=False)
    capacity = db.Column(db.Integer, default=4)
    status = db.Column(db.String(20), default='available')  # available, occupied, reserved

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_name = db.Column(db.String(100), default='Walk-in Customer')
    table_id = db.Column(db.Integer, db.ForeignKey('table.id'), nullable=True)
    subtotal = db.Column(db.Float, default=0)
    tax_rate = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    total = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='pending')  # pending, paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)

class BillItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UdhariEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    entry_type = db.Column(db.String(10), nullable=False)  # 'debit' = udhari dili, 'credit' = payment mila
    description = db.Column(db.String(200), nullable=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ===================== HELPERS =====================

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# Units per category
SHOP_UNITS = {
    'dairy': ['litre', 'ml', '500ml'],
    'grains': ['kg', 'gram', '500g'],
    'pulses': ['kg', 'gram'],
    'spices': ['gram', '100g'],
    'oil': ['litre', 'ml'],
    'other': ['piece', 'packet', 'kg', 'gram', 'litre']
}

RESTAURANT_UNITS = {
    'liquor': ['bottle', 'peg (30ml)', 'peg (60ml)', 'quarter', 'half'],
    'beer': ['bottle (650ml)', 'bottle (330ml)', 'pint'],
    'mocktail': ['glass', 'litre'],
    'cocktail': ['glass'],
    'food': ['plate', 'piece', 'bowl'],
    'soft_drink': ['bottle', 'can', 'glass']
}

# ===================== AUTH ROUTES =====================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_type'] = user.user_type
            session['business_name'] = user.business_name
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        business_name = request.form.get('business_name', '').strip()
        user_type = request.form.get('user_type', 'shop')
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        user = User(
            email=email,
            password=generate_password_hash(password),
            business_name=business_name,
            user_type=user_type
        )
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        session['user_type'] = user.user_type
        session['business_name'] = user.business_name
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ===================== DASHBOARD =====================

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    uid = user.id
    stock_count = StockItem.query.filter_by(user_id=uid).count()
    menu_count = MenuItem.query.filter_by(user_id=uid).count()
    low_stock = StockItem.query.filter(StockItem.user_id==uid, StockItem.quantity <= StockItem.min_stock).all()
    today = datetime.utcnow().date()
    bills_today = Bill.query.filter(
        Bill.user_id==uid,
        Bill.status=='paid',
        db.func.date(Bill.paid_at)==today
    ).all()
    revenue_today = sum(b.total for b in bills_today)
    pending_bills = Bill.query.filter_by(user_id=uid, status='pending').count()
    tables = []
    if user.user_type == 'restaurant':
        tables = Table.query.filter_by(user_id=uid).all()
    return render_template('dashboard.html', user=user,
        stock_count=stock_count, menu_count=menu_count,
        low_stock=low_stock, revenue_today=revenue_today,
        pending_bills=pending_bills, tables=tables, bills_today=len(bills_today))

# ===================== STOCK ROUTES =====================

@app.route('/stock')
@login_required
def stock():
    user = get_current_user()
    items = StockItem.query.filter_by(user_id=user.id).order_by(StockItem.category).all()
    units_map = SHOP_UNITS if user.user_type == 'shop' else RESTAURANT_UNITS
    return render_template('stock.html', user=user, items=items, units_map=units_map)

@app.route('/stock/add', methods=['POST'])
@login_required
def add_stock():
    user = get_current_user()
    data = request.get_json()
    item = StockItem(
        user_id=user.id,
        name=data['name'],
        category=data['category'],
        quantity=float(data['quantity']),
        unit=data['unit'],
        price=float(data['price']),
        min_stock=float(data.get('min_stock', 5))
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'id': item.id})

@app.route('/stock/update/<int:item_id>', methods=['POST'])
@login_required
def update_stock(item_id):
    user = get_current_user()
    item = StockItem.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    data = request.get_json()
    item.quantity = float(data.get('quantity', item.quantity))
    item.price = float(data.get('price', item.price))
    item.name = data.get('name', item.name)
    item.min_stock = float(data.get('min_stock', item.min_stock))
    db.session.commit()
    return jsonify({'success': True})

@app.route('/stock/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_stock(item_id):
    user = get_current_user()
    item = StockItem.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/stock/data')
@login_required
def stock_data():
    user = get_current_user()
    items = StockItem.query.filter_by(user_id=user.id).all()
    return jsonify([{
        'id': i.id, 'name': i.name, 'category': i.category,
        'quantity': i.quantity, 'unit': i.unit,
        'price': i.price, 'min_stock': i.min_stock,
        'low': i.quantity <= i.min_stock
    } for i in items])

# ===================== MENU ROUTES =====================

@app.route('/menu')
@login_required
def menu():
    user = get_current_user()
    items = MenuItem.query.filter_by(user_id=user.id).all()
    units_map = SHOP_UNITS if user.user_type == 'shop' else RESTAURANT_UNITS
    return render_template('menu.html', user=user, items=items, units_map=units_map)

@app.route('/menu/add', methods=['POST'])
@login_required
def add_menu():
    user = get_current_user()
    data = request.get_json()
    item = MenuItem(
        user_id=user.id,
        name=data['name'],
        category=data['category'],
        price=float(data['price']),
        unit=data['unit'],
        is_available=data.get('is_available', True)
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'id': item.id})

@app.route('/menu/toggle/<int:item_id>', methods=['POST'])
@login_required
def toggle_menu(item_id):
    user = get_current_user()
    item = MenuItem.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    item.is_available = not item.is_available
    db.session.commit()
    return jsonify({'success': True, 'available': item.is_available})

@app.route('/menu/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_menu(item_id):
    user = get_current_user()
    item = MenuItem.query.filter_by(id=item_id, user_id=user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/menu/data')
@login_required
def menu_data():
    user = get_current_user()
    items = MenuItem.query.filter_by(user_id=user.id, is_available=True).all()
    return jsonify([{
        'id': i.id, 'name': i.name, 'category': i.category,
        'price': i.price, 'unit': i.unit
    } for i in items])

# ===================== TABLE ROUTES (Restaurant Only) =====================

@app.route('/tables')
@login_required
def tables():
    user = get_current_user()
    if user.user_type != 'restaurant':
        return redirect(url_for('dashboard'))
    tbls = Table.query.filter_by(user_id=user.id).order_by(Table.table_number).all()
    return render_template('tables.html', user=user, tables=tbls)

@app.route('/tables/add', methods=['POST'])
@login_required
def add_table():
    user = get_current_user()
    data = request.get_json()
    t = Table(user_id=user.id, table_number=data['table_number'], capacity=int(data.get('capacity', 4)))
    db.session.add(t)
    db.session.commit()
    return jsonify({'success': True, 'id': t.id})

@app.route('/tables/status/<int:table_id>', methods=['POST'])
@login_required
def update_table_status(table_id):
    user = get_current_user()
    t = Table.query.filter_by(id=table_id, user_id=user.id).first_or_404()
    data = request.get_json()
    t.status = data['status']
    db.session.commit()
    return jsonify({'success': True})

@app.route('/tables/delete/<int:table_id>', methods=['POST'])
@login_required
def delete_table(table_id):
    user = get_current_user()
    t = Table.query.filter_by(id=table_id, user_id=user.id).first_or_404()
    db.session.delete(t)
    db.session.commit()
    return jsonify({'success': True})

# ===================== BILLING ROUTES =====================

@app.route('/billing')
@login_required
def billing():
    user = get_current_user()
    menu_items = MenuItem.query.filter_by(user_id=user.id, is_available=True).all()
    tables = []
    if user.user_type == 'restaurant':
        tables = Table.query.filter_by(user_id=user.id).all()
    pending_bills = Bill.query.filter_by(user_id=user.id, status='pending').order_by(Bill.created_at.desc()).all()
    return render_template('billing.html', user=user, menu_items=menu_items, tables=tables, pending_bills=pending_bills)

@app.route('/billing/create', methods=['POST'])
@login_required
def create_bill():
    user = get_current_user()
    data = request.get_json()
    bill = Bill(
        user_id=user.id,
        customer_name=data.get('customer_name', 'Walk-in Customer'),
        table_id=data.get('table_id') or None
    )
    db.session.add(bill)
    db.session.flush()
    subtotal = 0
    for item in data.get('items', []):
        sub = float(item['price']) * float(item['quantity'])
        bi = BillItem(
            bill_id=bill.id,
            item_name=item['name'],
            quantity=float(item['quantity']),
            unit=item['unit'],
            price=float(item['price']),
            subtotal=sub
        )
        db.session.add(bi)
        subtotal += sub
    tax_rate = float(data.get('tax_rate', 0))
    discount = float(data.get('discount', 0))
    tax_amount = subtotal * tax_rate / 100
    total = max(0, subtotal + tax_amount - discount)
    bill.subtotal = subtotal
    bill.tax_rate = tax_rate
    bill.tax_amount = tax_amount
    bill.discount = discount
    bill.total = total
    db.session.commit()
    return jsonify({'success': True, 'bill_id': bill.id, 'total': total})

@app.route('/billing/pay/<int:bill_id>', methods=['POST'])
@login_required
def pay_bill(bill_id):
    user = get_current_user()
    bill = Bill.query.filter_by(id=bill_id, user_id=user.id).first_or_404()
    bill.status = 'paid'
    bill.paid_at = datetime.utcnow()
    if bill.table_id:
        t = Table.query.get(bill.table_id)
        if t:
            t.status = 'available'
    db.session.commit()
    return jsonify({'success': True})

@app.route('/billing/bill/<int:bill_id>')
@login_required
def view_bill(bill_id):
    user = get_current_user()
    bill = Bill.query.filter_by(id=bill_id, user_id=user.id).first_or_404()
    items = BillItem.query.filter_by(bill_id=bill_id).all()
    table = Table.query.get(bill.table_id) if bill.table_id else None
    return render_template('bill_detail.html', user=user, bill=bill, items=items, table=table)

@app.route('/billing/history')
@login_required
def billing_history():
    user = get_current_user()
    bills = Bill.query.filter_by(user_id=user.id, status='paid').order_by(Bill.paid_at.desc()).limit(50).all()
    return render_template('billing_history.html', user=user, bills=bills)


# ===================== CUSTOMER ROUTES =====================

@app.route('/customers')
@login_required
def customers():
    user = get_current_user()
    custs = Customer.query.filter_by(user_id=user.id).order_by(Customer.name).all()
    cust_data = []
    for c in custs:
        entries = UdhariEntry.query.filter_by(customer_id=c.id).all()
        balance = sum(e.amount if e.entry_type == 'debit' else -e.amount for e in entries)
        cust_data.append({'customer': c, 'balance': balance})
    return render_template('customers.html', user=user, cust_data=cust_data)

@app.route('/customers/add', methods=['POST'])
@login_required
def add_customer():
    user = get_current_user()
    data = request.get_json()
    c = Customer(
        user_id=user.id,
        name=data['name'],
        phone=data.get('phone', ''),
        address=data.get('address', ''),
        notes=data.get('notes', '')
    )
    db.session.add(c)
    db.session.commit()
    return jsonify({'success': True, 'id': c.id, 'name': c.name})

@app.route('/customers/edit/<int:cust_id>', methods=['POST'])
@login_required
def edit_customer(cust_id):
    user = get_current_user()
    c = Customer.query.filter_by(id=cust_id, user_id=user.id).first_or_404()
    data = request.get_json()
    c.name = data.get('name', c.name)
    c.phone = data.get('phone', c.phone)
    c.address = data.get('address', c.address)
    c.notes = data.get('notes', c.notes)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/customers/delete/<int:cust_id>', methods=['POST'])
@login_required
def delete_customer(cust_id):
    user = get_current_user()
    c = Customer.query.filter_by(id=cust_id, user_id=user.id).first_or_404()
    UdhariEntry.query.filter_by(customer_id=cust_id).delete()
    db.session.delete(c)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/customers/list')
@login_required
def customers_list():
    user = get_current_user()
    custs = Customer.query.filter_by(user_id=user.id).order_by(Customer.name).all()
    return jsonify([{'id': c.id, 'name': c.name, 'phone': c.phone or ''} for c in custs])

@app.route('/customers/<int:cust_id>')
@login_required
def customer_detail(cust_id):
    user = get_current_user()
    c = Customer.query.filter_by(id=cust_id, user_id=user.id).first_or_404()
    entries = UdhariEntry.query.filter_by(customer_id=cust_id).order_by(UdhariEntry.created_at.desc()).all()
    balance = sum(e.amount if e.entry_type == 'debit' else -e.amount for e in entries)
    return render_template('customer_detail.html', user=user, customer=c, entries=entries, balance=balance)

# ===================== UDHARI ROUTES =====================

@app.route('/udhari/add', methods=['POST'])
@login_required
def add_udhari():
    user = get_current_user()
    data = request.get_json()
    entry = UdhariEntry(
        user_id=user.id,
        customer_id=int(data['customer_id']),
        amount=float(data['amount']),
        entry_type=data['entry_type'],
        description=data.get('description', ''),
        bill_id=data.get('bill_id') or None
    )
    db.session.add(entry)
    db.session.commit()
    entries = UdhariEntry.query.filter_by(customer_id=entry.customer_id).all()
    balance = sum(e.amount if e.entry_type == 'debit' else -e.amount for e in entries)
    return jsonify({'success': True, 'balance': balance})

@app.route('/udhari/delete/<int:entry_id>', methods=['POST'])
@login_required
def delete_udhari(entry_id):
    user = get_current_user()
    entry = UdhariEntry.query.filter_by(id=entry_id, user_id=user.id).first_or_404()
    cust_id = entry.customer_id
    db.session.delete(entry)
    db.session.commit()
    entries = UdhariEntry.query.filter_by(customer_id=cust_id).all()
    balance = sum(e.amount if e.entry_type == 'debit' else -e.amount for e in entries)
    return jsonify({'success': True, 'balance': balance})

# ===================== INIT =====================

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# Already defined above - just ensuring db tables are created
