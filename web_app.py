from flask import Flask, request, redirect
import sqlite3
import csv
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
from functools import wraps

app = Flask(__name__)
app.secret_key = "greenleaf_secret_key_change_later"
# Create users table for Admin and Cashier login
def create_users_table():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'cashier'))
        )
    """)

    connection.commit()
    connection.close()


create_users_table()
def role_required(*allowed_roles):
    def decorator(view_function):
        @wraps(view_function)
        def wrapped_view(*args, **kwargs):

            if "user_id" not in session:
                return redirect("/login")

            if session.get("role") not in allowed_roles:
                return "Access denied! You do not have permission.", 403

            return view_function(*args, **kwargs)

        return wrapped_view

    return decorator


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        connection = sqlite3.connect("greenleaf.db")
        cursor = connection.cursor()

        cursor.execute(
            "SELECT user_id, username, password_hash, role "
            "FROM users WHERE username = ?",
            (username,)
        )

        user = cursor.fetchone()
        connection.close()

        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            session["username"] = user[1]
            session["role"] = user[3]

            return redirect("/dashboard")

        return "Invalid username or password. Please try again."

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GreenLeaf Login</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>Login</h2>

        <form method="POST">
            <label>Username:</label><br>
            <input type="text" name="username" required>
            <br><br>

            <label>Password:</label><br>
            <input type="password" name="password" required>
            <br><br>

            <button type="submit">Login</button>
        </form>
    </body>
    </html>
    """
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")   
@app.route("/setup_users")
def setup_users():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    users = [
        ("admin", generate_password_hash("Admin@123"), "admin"),
        ("cashier", generate_password_hash("Cashier@123"), "cashier")
    ]

    for username, password_hash, role in users:
        cursor.execute("""
            INSERT OR IGNORE INTO users
            (username, password_hash, role)
            VALUES (?, ?, ?)
        """, (username, password_hash, role))

    connection.commit()
    connection.close()

    return "Demo users created! You can now log in."    
@app.route("/products")
@role_required("admin")
def products():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()

    query = """
        SELECT *
        FROM products
        WHERE name LIKE ?
    """
    params = [f"%{search}%"]

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY name"

    cursor.execute(query, params)
    all_products = cursor.fetchall()

    cursor.execute("""
        SELECT DISTINCT category
        FROM products
        ORDER BY category
    """)
    categories = cursor.fetchall()

    connection.close()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GreenLeaf Products</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>Product Inventory</h2>

        <a href="/add_product">➕ Add New Product</a>
        <br><br>

        <a href="/export_products">💾 Export Products to Excel</a>
        <br><br>

        <form action="/products" method="GET">
            <label>Search Product:</label>
            <input
                type="text"
                name="search"
                placeholder="Enter product name"
                value="SEARCH_VALUE"
            >

            <label>Category:</label>
            <select name="category">
                <option value="">All Categories</option>
                CATEGORY_OPTIONS
            </select>

            <button type="submit">Search / Filter</button>
            <a href="/products">Clear</a>
        </form>

        <br>
        <table border="1" cellpadding="10">
            <tr>
                <th>ID</th>
                <th>Product Name</th>
                <th>Category</th>
                <th>Price (₹)</th>
                <th>Stock</th>
                <th>Stock Action</th>
                <th>Actions</th>
            </tr>
    """

    html = html.replace(
        "SEARCH_VALUE",
        search.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )

    category_options = ""

    for item in categories:
        category_name = item[0]
        safe_category = (
            category_name.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

        selected = "selected" if category_name == category else ""

        category_options += (
            f'<option value="{safe_category}" {selected}>'
            f'{safe_category}</option>'
        )

    html = html.replace("CATEGORY_OPTIONS", category_options)

    for product in all_products:
        html += f"""
            <tr>
                <td>{product[0]}</td>
                <td>{product[1]}</td>
                <td>{product[2]}</td>
                <td>{product[3]}</td>
                <td>{product[4]}</td>
                <td>
                    {"⚠️ LOW STOCK" if product[4] <= 10 else "✅ STOCK OK"}
                </td>
                <td>
                    <a href="/edit_product/{product[0]}">Edit</a>

                    <form action="/delete_product/{product[0]}" method="POST"
                          style="display: inline;"
                          onsubmit="return confirm('Are you sure you want to delete this product?')">
                        <button type="submit">Delete</button>
                    </form>
                </td>
            </tr>
        """

    if not all_products:
        html += """
            <tr>
                <td colspan="7">No matching products found.</td>
            </tr>
        """

    html += """
        </table>
        <br>
        <a href="/">Back to Home</a>
    </body>
    </html>
    """

    return html

@app.route("/add_product", methods=["GET", "POST"])
@role_required("admin")
def add_product():
    return """
    <html>
    <head>
        <title>Add Product</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>Add New Product</h2>

<form action="/save_product" method="POST" style="width: 320px; margin: 20px auto; text-align: left;">

    <label for="name">Product Name:</label>
    <input type="text" id="name" name="name" placeholder="Enter product name" required style="width: 100%; box-sizing: border-box;">

    <br><br>

    <label for="category">Category:</label>
    <input type="text" id="category" name="category" placeholder="Enter category" required style="width: 100%; box-sizing: border-box;">

    <br><br>

    <label for="price">Price (₹):</label>
    <input type="number" id="price" name="price" placeholder="Enter price" step="0.01" min="0.01" required style="width: 100%; box-sizing: border-box;">

    <br><br>

    <label for="stock_qty">Stock Quantity:</label>
    <input type="number" id="stock_qty" name="stock_qty" placeholder="Enter stock quantity" min="0" required style="width: 100%; box-sizing: border-box;">

    <br><br>

    <button type="submit">Add Product</button>

</form>

        <br>
        <a href="/products">View Products</a>
        <br>
        <a href="/">Home</a>
    </body>
    </html>
    """

@app.route("/save_product", methods=["POST"])
@role_required("admin")
def save_product():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()

    try:
        price = float(request.form.get("price", ""))
        stock_qty = int(request.form.get("stock_qty", ""))
    except ValueError:
        return "Error: Enter a valid price and stock quantity.", 400

    # Validate product name and category
    if not name or not category:
        return "Error: Product name and category are required.", 400

    # Validate price
    if price <= 0:
        return "Error: Price must be greater than zero.", 400

    # Validate stock quantity
    if stock_qty < 0:
        return "Error: Stock quantity cannot be negative.", 400

    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    try:
        cursor.execute(
            "INSERT INTO products (name, category, price, stock_qty) VALUES (?, ?, ?, ?)",
            (name, category, price, stock_qty)
        )
        connection.commit()

    except sqlite3.IntegrityError:
        connection.rollback()
        connection.close()
        return "Error: This product may already exist.", 400

    finally:
        if connection:
            connection.close()

    return redirect("/products")

@app.route("/delete_product/<int:product_id>", methods=["POST"])
@role_required("admin")
def delete_product(product_id):
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM products WHERE product_id = ?",
        (product_id,)
    )

    connection.commit()
    deleted_rows = cursor.rowcount
    connection.close()

    if deleted_rows == 0:
        return "Product not found!", 404

    return redirect("/products")
@app.route("/edit_product/<int:product_id>", methods=["GET", "POST"])
@role_required("admin")
def edit_product(product_id):
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM products WHERE product_id = ?",
        (product_id,)
    )
    product = cursor.fetchone()
    connection.close()

    if product is None:
        return "Product not found!"

    return f"""
    <html>
    <head>
        <title>Edit Product</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>Edit Product</h2>

        <form action="/update_product/{product[0]}" method="POST"
      style="width: 320px; margin: 20px auto; text-align: left;">

    <label for="name">Product Name:</label>
    <input type="text" id="name" name="name"
           value="{product[1]}" required
           style="width: 100%; box-sizing: border-box;">

    <br><br>

    <label for="category">Category:</label>
    <input type="text" id="category" name="category"
           value="{product[2]}" required
           style="width: 100%; box-sizing: border-box;">

    <br><br>

    <label for="price">Price (₹):</label>
    <input type="number" id="price" name="price"
           value="{product[3]}" step="0.01" min="0.01" required
           style="width: 100%; box-sizing: border-box;">

    <br><br>

    <label for="stock_qty">Stock Quantity:</label>
    <input type="number" id="stock_qty" name="stock_qty"
           value="{product[4]}" min="0" required
           style="width: 100%; box-sizing: border-box;">

    <br><br>

    <button type="submit">Save Changes</button>
</form>
        <a href="/products">Back to Products</a>
    </body>
    </html>
    """  
@app.route("/update_product/<int:product_id>", methods=["POST"])
@role_required("admin")
def update_product(product_id):
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()

    try:
        price = float(request.form.get("price", ""))
        stock_qty = int(request.form.get("stock_qty", ""))
    except ValueError:
        return "Error: Enter a valid price and stock quantity.", 400

    # Validate product name and category
    if not name or not category:
        return "Error: Product name and category are required.", 400

    # Validate price
    if price <= 0:
        return "Error: Price must be greater than zero.", 400

    # Validate stock quantity
    if stock_qty < 0:
        return "Error: Stock quantity cannot be negative.", 400

    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            UPDATE products
            SET name = ?, category = ?, price = ?, stock_qty = ?
            WHERE product_id = ?
            """,
            (name, category, price, stock_qty, product_id)
        )

        if cursor.rowcount == 0:
            connection.close()
            return "Product not found!", 404

        connection.commit()

    except sqlite3.IntegrityError:
        connection.rollback()
        return "Error: A product with this name may already exist.", 400

    finally:
        connection.close()

    return redirect("/products")

@app.route("/billing")
@role_required("admin", "cashier")
def billing():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT product_id, name, price, stock_qty
        FROM products
        WHERE stock_qty > 0
        ORDER BY name
    """)

    products = cursor.fetchall()
    connection.close()

    rows = ""

    for product in products:
        rows += f"""
        <tr>
            <td>{product[1]}</td>
            <td>₹{product[2]:.2f}</td>
            <td>{product[3]}</td>
            <td>
                <input type="number"
                       name="quantity_{product[0]}"
                       min="0"
                       max="{product[3]}"
                       value="0">
            </td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>GreenLeaf Billing</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>Multiple Products Billing</h2>

        <form action="/create_bill" method="POST">
            <table border="1" cellpadding="10">
                <tr>
                    <th>Product</th>
                    <th>Price</th>
                    <th>Available Stock</th>
                    <th>Quantity to Buy</th>
                </tr>
                {rows}
            </table>

            <br>

            <label>Discount (%):</label>
            <input type="number"
                   name="discount"
                   min="0"
                   max="100"
                   step="0.01"
                   value="0"
                   required>

            <br><br>
            <button type="submit">Generate Bill</button>
        </form>

        <br>
        <a href="/products">View Products</a>
        <br><br>
        <a href="/">Home</a>
    </body>
    </html>
    """
@app.route("/create_bill", methods=["POST"])
def create_bill():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    try:
        discount = float(request.form.get("discount", "0"))

        if not 0 <= discount <= 100:
            return "Invalid discount! Enter a value between 0 and 100."

        cursor.execute("""
            SELECT product_id, name, price, stock_qty
            FROM products
            WHERE stock_qty > 0
        """)

        products = cursor.fetchall()
        selected_items = []
        subtotal = 0

        for product_id, name, price, stock_qty in products:
            quantity_text = request.form.get(
                f"quantity_{product_id}", "0"
            ).strip()

            if quantity_text == "":
                quantity_text = "0"

            quantity = int(quantity_text)

            if quantity < 0:
                return "Quantity cannot be negative!"

            if quantity == 0:
                continue

            if quantity > stock_qty:
                return (
                    f"Insufficient stock for {name}. "
                    f"Available stock: {stock_qty}"
                )

            item_total = price * quantity

            selected_items.append({
                "product_id": product_id,
                "name": name,
                "price": price,
                "quantity": quantity,
                "item_total": item_total
            })

            subtotal += item_total
   

        if not selected_items:
            return "Please select at least one product!"

        discount_amount = subtotal * discount / 100
        final_total = subtotal - discount_amount

        # Save the overall bill first.
        cursor.execute("""
            INSERT INTO bills (
                subtotal,
                discount_percent,
                discount_amount,
                total_amount
            )
            VALUES (?, ?, ?, ?)
        """, (
            subtotal,
            discount,
            discount_amount,
            final_total
        ))

        bill_id = cursor.lastrowid

        # Save each product in this bill.
        for item in selected_items:
            cursor.execute("""
                INSERT INTO sale_items (
                    bill_id,
                    product_id,
                    quantity,
                    price
                )
                VALUES (?, ?, ?, ?)
            """, (
                bill_id,
                item["product_id"],
                item["quantity"],
                item["price"]
            ))

            # Keep the existing sales table updated.
            # Store each item's amount after proportional discount.
            item_discount = (
                item["item_total"] * discount / 100
            )
            discounted_item_total = (
                item["item_total"] - item_discount
            )

            cursor.execute("""
                INSERT INTO sales (
                    product_id,
                    product_name,
                    quantity,
                    unit_price,
                    total_amount
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                item["product_id"],
                item["name"],
                item["quantity"],
                item["price"],
                discounted_item_total
            ))

            # Reduce stock only when enough stock is available.
            cursor.execute("""
                UPDATE products
                SET stock_qty = stock_qty - ?
                WHERE product_id = ?
                  AND stock_qty >= ?
            """, (
                item["quantity"],
                item["product_id"],
                item["quantity"]
            ))

            if cursor.rowcount != 1:
                raise ValueError(
                    f"Stock update failed for {item['name']}."
                )

        # Save all changes together.
        connection.commit()

        bill_rows = ""

        for item in selected_items:
            bill_rows += f"""
            <tr>
                <td>{item["name"]}</td>
                <td>{item["quantity"]}</td>
                <td>₹{item["price"]:.2f}</td>
                <td>₹{item["item_total"]:.2f}</td>
            </tr>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>GreenLeaf Bill</title>
            <link rel="stylesheet" href="/static/style.css">
        </head>
        <body>
            <h1>🌿 GreenLeaf Grocers</h1>
            <h2>Bill Generated Successfully!</h2>
            <h3>Bill Number: {bill_id}</h3>

            <table border="1" cellpadding="10">
                <tr>
                    <th>Product</th>
                    <th>Quantity</th>
                    <th>Unit Price</th>
                    <th>Amount</th>
                </tr>
                {bill_rows}
            </table>

            <h3>Subtotal: ₹{subtotal:.2f}</h3>
            <h3>Discount: {discount:.2f}%</h3>
            <h3>Discount Amount: ₹{discount_amount:.2f}</h3>
            <h2>Total Amount: ₹{final_total:.2f}</h2>

            <button onclick="window.print()">Print Bill</button>
            <a href="/download_bill/{bill_id}">
    <button type="button">Download Bill CSV</button>
</a>

            <br><br>
            <a href="/billing">Create Another Bill</a>
            <br><br>
            <a href="/sales">View Sales History</a>
            <br><br>
            <a href="/products">View Products</a>
            <br><br>
            <a href="/">Home</a>
        </body>
        </html>
        """

  
    except (ValueError, TypeError) as e:
        connection.rollback()
        return f"Invalid input: {type(e).__name__}: {e}", 400


    except Exception:
        connection.rollback()
        app.logger.exception("Bill generation failed")
        return (
            "Bill generation failed. "
            "No changes were saved. Please try again."
        )

    finally:
        connection.close()
@app.route("/download_bill/<int:bill_id>")
def download_bill(bill_id):
    import io
    from flask import Response

    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT subtotal, discount_percent,
               discount_amount, total_amount
        FROM bills
        WHERE bill_id = ?
    """, (bill_id,))

    bill = cursor.fetchone()

    if bill is None:
        connection.close()
        return "Bill not found!", 404

    cursor.execute("""
        SELECT p.name, si.quantity, si.price
        FROM sale_items si
        JOIN products p ON si.product_id = p.product_id
        WHERE si.bill_id = ?
    """, (bill_id,))

    items = cursor.fetchall()
    connection.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["GreenLeaf Grocers - Bill"])
    writer.writerow(["Bill Number", bill_id])
    writer.writerow([])
    writer.writerow([
        "Product", "Quantity", "Unit Price", "Amount"
    ])

    for name, quantity, price in items:
        writer.writerow([
            name,
            quantity,
            f"{price:.2f}",
            f"{quantity * price:.2f}"
        ])

    writer.writerow([])
    writer.writerow(["Subtotal", f"{bill[0]:.2f}"])
    writer.writerow(["Discount (%)", f"{bill[1]:.2f}"])
    writer.writerow(["Discount Amount", f"{bill[2]:.2f}"])
    writer.writerow(["Final Total", f"{bill[3]:.2f}"])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                f"attachment; filename=GreenLeaf_Bill_{bill_id}.csv"
        }
    )
        
@app.route("/sales")
@role_required("admin", "cashier")
def sales():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT bill_id, subtotal, discount_percent,
               discount_amount, total_amount
        FROM bills
        ORDER BY bill_id DESC
    """)

    all_bills = cursor.fetchall()

    bill_rows = ""

    for bill in all_bills:
        bill_rows += f"""
        <tr>
            <td>{bill[0]}</td>
            <td>₹{bill[1]:.2f}</td>
            <td>{bill[2]:.2f}%</td>
            <td>₹{bill[3]:.2f}</td>
            <td>₹{bill[4]:.2f}</td>
        </tr>
        """

    cursor.execute("""
        SELECT sale_id, product_name, quantity,
               unit_price, total_amount, sale_date
        FROM sales
        ORDER BY sale_id DESC
    """)

    all_sales = cursor.fetchall()
    connection.close()

    rows = ""

    for sale in all_sales:
        rows += f"""
        <tr>
            <td>{sale[0]}</td>
            <td>{sale[1]}</td>
            <td>{sale[2]}</td>
            <td>₹{sale[3]:.2f}</td>
            <td>₹{sale[4]:.2f}</td>
            <td>{sale[5]}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
        <title>Sales History</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>Sales History</h2>
        <h2>Bill Summary & Discount Details</h2>

        <table>
            <tr>
                <th>Bill Number</th>
                <th>Subtotal</th>
                <th>Discount %</th>
                <th>Discount Amount</th>
                <th>Final Total</th>
            </tr>
            {bill_rows}
        </table>

        <br>
        <table>
            <tr>
                <th>Sale ID</th>
                <th>Product</th>
                <th>Quantity</th>
                <th>Unit Price</th>
                <th>Total Amount</th>
                <th>Sale Date</th>
            </tr>
            {rows}
        </table>

        <br>
        <a href="/billing">Create New Bill</a>
        <br><br>
        <a href="/products">View Products</a>
    </body>
    </html>
    """
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    # 1. Total Products
    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]

    # 2. Total Revenue from existing sales records
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0)
        FROM sales
    """)
    total_revenue = cursor.fetchone()[0]

    # 3. Total Bills
    # Bills table is preferred when bills exist.
    cursor.execute("SELECT COUNT(*) FROM bills")
    bills_count = cursor.fetchone()[0]

    if bills_count > 0:
        total_bills = bills_count
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0)
            FROM bills
        """)
        total_revenue = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COALESCE(AVG(total_amount), 0)
            FROM bills
        """)
        average_bill_value = cursor.fetchone()[0]
    else:
        # Fallback to legacy sales records until bills are saved correctly.
        cursor.execute("SELECT COUNT(*) FROM sales")
        total_bills = cursor.fetchone()[0]

        if total_bills > 0:
            average_bill_value = total_revenue / total_bills
        else:
            average_bill_value = 0

    # 4. Low Stock Products
    cursor.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE stock_qty <= COALESCE(reorder_level, 10)
    """)
    low_stock_count = cursor.fetchone()[0]

    connection.close()

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>GreenLeaf Dashboard</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <a href="/logout">Logout</a>
        <h2>📊 Business Dashboard</h2>

        <div class="dashboard-card">
            <h3>🛒 Total Products</h3>
            <h2>{total_products}</h2>
        </div>

        <div class="dashboard-card">
            <h3>💰 Total Revenue</h3>
            <h2>₹{total_revenue:.2f}</h2>
        </div>

        <div class="dashboard-card">
            <h3>🧾 Total Bills / Sales Records</h3>
            <h2>{total_bills}</h2>
        </div>

        <div class="dashboard-card">
            <h3>📈 Average Bill Value</h3>
            <h2>₹{average_bill_value:.2f}</h2>
        </div>

        <div class="dashboard-card">
            <h3>⚠️ Low Stock Products</h3>
            <h2>{low_stock_count}</h2>
        </div>

        <hr>

        <h3>📦 Inventory Management</h3>
        <a href="/products">View All Products</a>
        <br><br>
        <a href="/low_stock">Low Stock Report</a>
        <br><br>
        <a href="/expiry_alerts">Product Expiry Alerts</a>
        <br><br>
        <a href="/export_products">Export Products to CSV</a>

        <hr>

        <h3>💰 Sales Reports</h3>
        <a href="/billing">Create New Bill</a>
        <br><br>
        <a href="/sales">Sales History</a>
        <br><br>
        <a href="/daily_sales">Daily Sales Report</a>
        <br><br>
        <a href="/monthly_sales">Monthly Sales Report</a>
        <br><br>
        <a href="/category_sales">Category-wise Sales</a>
        <br><br>
        <a href="/top_products">Top-Selling Products</a>

    </body>
    </html>
    """
@app.route("/analytics")
@role_required("admin", "cashier")
def analytics():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    start_date = request.args.get("start_date", "2000-01-01")
    end_date = request.args.get("end_date", "2099-12-31")
    view = request.args.get("view", "revenue")

    if view not in ["revenue", "quantity"]:
        view = "revenue"

    cursor.execute("""
        SELECT DATE(sale_date),
               SUM(total_amount),
               SUM(quantity)
        FROM sales
        WHERE DATE(sale_date) BETWEEN ? AND ?
        GROUP BY DATE(sale_date)
        ORDER BY DATE(sale_date)
    """, (start_date, end_date))

    daily_data = cursor.fetchall()

    cursor.execute("""
        SELECT p.category,
               SUM(s.total_amount),
               SUM(s.quantity)
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        WHERE DATE(s.sale_date) BETWEEN ? AND ?
        GROUP BY p.category
        ORDER BY p.category
    """, (start_date, end_date))

    category_data = cursor.fetchall()
    connection.close()

    daily_labels = [str(row[0]) for row in daily_data]

    if view == "quantity":
        daily_values = [int(row[2] or 0) for row in daily_data]
        category_values = [int(row[2] or 0) for row in category_data]
        metric_title = "Quantity Sold"
        axis_title = "Quantity"
    else:
        daily_values = [float(row[1] or 0) for row in daily_data]
        category_values = [float(row[1] or 0) for row in category_data]
        metric_title = "Revenue"
        axis_title = "Revenue (₹)"

    category_labels = [str(row[0]) for row in category_data]

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GreenLeaf Analytics</title>
        <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>Sales Analytics Dashboard</h2>

        <form method="GET" action="/analytics">
            <label>Start Date:</label>
            <input type="date" name="start_date" value="START_DATE">

            <label>End Date:</label>
            <input type="date" name="end_date" value="END_DATE">

            <label>View:</label>
            <select name="view">
                <option value="revenue" REVENUE_SELECTED>Revenue</option>
                <option value="quantity" QUANTITY_SELECTED>Quantity</option>
            </select>

            <button type="submit">Apply Filter</button>
            <a href="/analytics">Reset</a>
        </form>

        <h3>Daily METRIC_TITLE</h3>
        <div id="dailyChart"
             style="width:100%;max-width:900px;height:400px;"></div>

        <h3>Category-wise METRIC_TITLE</h3>
        <div id="categoryChart"
             style="width:100%;max-width:900px;height:400px;"></div>

        <br>
        <a href="/dashboard">Back to Dashboard</a>

        <script>
            const dailyLabels = DAILY_LABELS;
            const dailyValues = DAILY_VALUES;
            const categoryLabels = CATEGORY_LABELS;
            const categoryValues = CATEGORY_VALUES;

            Plotly.newPlot('dailyChart', [{
                x: dailyLabels,
                y: dailyValues,
                type: 'bar',
                name: 'METRIC_TITLE'
            }], {
                title: 'Daily METRIC_TITLE',
                xaxis: {title: 'Date'},
                yaxis: {title: 'AXIS_TITLE'}
            }, {responsive: true});

            Plotly.newPlot('categoryChart', [{
                labels: categoryLabels,
                values: categoryValues,
                type: 'pie',
                hole: 0.35
            }], {
                title: 'Category-wise METRIC_TITLE'
            }, {responsive: true});
        </script>
    </body>
    </html>
    """

    html = html.replace("START_DATE", start_date)
    html = html.replace("END_DATE", end_date)
    html = html.replace("REVENUE_SELECTED",
                        "selected" if view == "revenue" else "")
    html = html.replace("QUANTITY_SELECTED",
                        "selected" if view == "quantity" else "")
    html = html.replace("METRIC_TITLE", metric_title)
    html = html.replace("AXIS_TITLE", axis_title)
    html = html.replace("DAILY_LABELS", json.dumps(daily_labels))
    html = html.replace("DAILY_VALUES", json.dumps(daily_values))
    html = html.replace("CATEGORY_LABELS", json.dumps(category_labels))
    html = html.replace("CATEGORY_VALUES", json.dumps(category_values))

    return html
@app.route("/low_stock")
@role_required("admin", "cashier")
def low_stock():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT product_id, name, category, stock_qty, reorder_level
        FROM products
        WHERE stock_qty <= reorder_level
        ORDER BY stock_qty ASC
    """)

    products_data = cursor.fetchall()
    connection.close()

    rows = ""

    for product in products_data:
        rows += f"""
        <tr>
            <td>{product[0]}</td>
            <td>{product[1]}</td>
            <td>{product[2]}</td>
            <td>{product[3]}</td>
            <td>{product[4]}</td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="5">No low-stock products available.</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Low Stock Report</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>⚠️ Low Stock Report</h2>

        <table border="1" cellpadding="10">
            <tr>
                <th>Product ID</th>
                <th>Product Name</th>
                <th>Category</th>
                <th>Current Stock</th>
                <th>Reorder Level</th>
            </tr>
            {rows}
        </table>

        <br>
        <a href="/">Back to Home</a>
    </body>
    </html>
    """
@app.route("/export_products")
@role_required("admin")
def export_products():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT product_id, name, category, price, stock_qty
        FROM products
        ORDER BY product_id
    """)

    products = cursor.fetchall()
    connection.close()

    from flask import Response
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Product ID",
        "Product Name",
        "Category",
        "Price",
        "Stock Quantity"
    ])

    writer.writerows(products)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=greenleaf_products.csv"
        }
    )
@app.route("/import_products", methods=["GET", "POST"])
def import_products():
    if request.method == "GET":
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Import Products</title>
            <link rel="stylesheet" href="/static/style.css">
        </head>
        <body>
            <h1>🌿 GreenLeaf Grocers</h1>
            <h2>Import Products from CSV</h2>

            <p>CSV file must contain these columns:</p>
            <p>Product Name, Category, Price, Stock Quantity</p>

            <form method="POST" enctype="multipart/form-data">
                <input type="file" name="file" accept=".csv" required>
                <button type="submit">Import Products</button>
            </form>

            <br>
            <a href="/products">Back to Products</a>
        </body>
        </html>
        """

    file = request.files.get("file")

    if not file or not file.filename:
        return "Please select a CSV file."

    if not file.filename.lower().endswith(".csv"):
        return "Invalid file! Please upload a CSV file."

    try:
        import io

        stream = io.StringIO(
            file.stream.read().decode("utf-8-sig")
        )
        reader = csv.DictReader(stream)

        required_columns = {
            "Product Name",
            "Category",
            "Price",
            "Stock Quantity"
        }

        if not reader.fieldnames or not required_columns.issubset(
            set(reader.fieldnames)
        ):
            return (
                "Invalid CSV columns. Required: "
                "Product Name, Category, Price, Stock Quantity"
            )

        connection = sqlite3.connect("greenleaf.db")
        cursor = connection.cursor()

        imported = 0
        skipped = 0

        for row in reader:
            try:
                name = (row.get("Product Name") or "").strip()
                category = (row.get("Category") or "").strip()
                price = float(row.get("Price", ""))
                stock_qty = int(row.get("Stock Quantity", ""))

                if (
                    not name
                    or not category
                    or price < 0
                    or stock_qty < 0
                ):
                    skipped += 1
                    continue

                cursor.execute("""
                    INSERT INTO products (
                        name, category, price, stock_qty
                    )
                    VALUES (?, ?, ?, ?)
                """, (name, category, price, stock_qty))

                imported += 1

            except (ValueError, TypeError):
                skipped += 1
            except sqlite3.IntegrityError:
                skipped += 1

        connection.commit()
        connection.close()

        return f"""
        <h1>CSV Import Completed!</h1>
        <p>Products imported: {imported}</p>
        <p>Rows skipped: {skipped}</p>
        <a href="/products">View Products</a>
        """

    except (UnicodeDecodeError, csv.Error):
        return "Unable to read this CSV file. Please check its format."   
@app.route("/category_sales")
@role_required("admin", "cashier")
def category_sales():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            p.category,
            SUM(s.quantity) AS total_quantity,
            SUM(s.total_amount) AS total_revenue
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        GROUP BY p.category
        ORDER BY total_revenue DESC
    """)

    categories = cursor.fetchall()

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0)
        FROM sales
    """)

    total_revenue = cursor.fetchone()[0]
    connection.close()

    rows = ""

    for category in categories:
        category_name = category[0]
        quantity_sold = category[1] or 0
        revenue = category[2] or 0

        if total_revenue > 0:
            percentage = (revenue / total_revenue) * 100
        else:
            percentage = 0

        rows += f"""
        <tr>
            <td>{category_name}</td>
            <td>{quantity_sold}</td>
            <td>₹{revenue:.2f}</td>
            <td>{percentage:.2f}%</td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="4">No category sales available.</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Category Sales Analytics</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>📊 Category-wise Sales Analytics</h2>

        <p><b>Total Sales Revenue:</b> ₹{total_revenue:.2f}</p>

        <table border="1" cellpadding="10">
            <tr>
                <th>Category</th>
                <th>Quantity Sold</th>
                <th>Total Revenue</th>
                <th>Sales Share</th>
            </tr>
            {rows}
        </table>

        <br>
        <a href="/dashboard">Back to Dashboard</a>
        <br><br>
        <a href="/products">View Products</a>
    </body>
    </html>
    """
@app.route("/daily_sales")
@role_required("admin", "cashier")
def daily_sales():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            DATE(sale_date) AS sales_day,
            COUNT(*) AS total_bills,
            COALESCE(SUM(total_amount), 0) AS total_revenue
        FROM bills
        GROUP BY DATE(sale_date)
        ORDER BY DATE(sale_date) DESC
    """)

    sales_data = cursor.fetchall()
    connection.close()

    rows = ""

    for sale in sales_data:
        rows += f"""
        <tr>
            <td>{sale[0]}</td>
            <td>{sale[1]}</td>
            <td>₹{sale[2]:.2f}</td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="3">No sales records available.</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Daily Sales Report</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>📅 Daily Sales Report</h2>

        <table border="1" cellpadding="10">
            <tr>
                <th>Date</th>
                <th>Total Bills</th>
                <th>Total Revenue</th>
            </tr>
            {rows}
        </table>

        <br>
        <a href="/dashboard">Back to Dashboard</a>
        <br><br>
        <a href="/sales">Sales History</a>
        <br><br>
        <a href="/monthly_sales">Monthly Sales Report</a>
    </body>
    </html>
    """

@app.route("/monthly_sales")
@role_required("admin", "cashier")
def monthly_sales():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            strftime('%Y-%m', sale_date),
            COUNT(*),
            SUM(total_amount)
        FROM sales
        GROUP BY strftime('%Y-%m', sale_date)
        ORDER BY strftime('%Y-%m', sale_date) DESC
    """)

    sales_data = cursor.fetchall()
    connection.close()

    rows = ""

    for sale in sales_data:
        rows += f"""
        <tr>
            <td>{sale[0]}</td>
            <td>{sale[1]}</td>
            <td>₹{sale[2]:.2f}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
        <title>Monthly Sales Report</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>📊 Monthly Sales Report</h2>

        <table border="1" cellpadding="10">
            <tr>
                <th>Month</th>
                <th>Total Bills</th>
                <th>Total Revenue</th>
            </tr>
            {rows}
        </table>

        <br>
        <a href="/dashboard">Back to Dashboard</a>
        <br><br>
        <a href="/daily_sales">Daily Sales Report</a>
    </body>
    </html>
    """  
@app.route("/top_products")
@role_required("admin", "cashier")
def top_products():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            product_name,
            SUM(quantity) AS total_quantity,
            SUM(total_amount) AS total_revenue
        FROM sales
        GROUP BY product_name
        ORDER BY total_quantity DESC
        LIMIT 10
    """)

    products_data = cursor.fetchall()
    connection.close()

    rows = ""

    for product in products_data:
        rows += f"""
        <tr>
            <td>{product[0]}</td>
            <td>{product[1]}</td>
            <td>₹{product[2]:.2f}</td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="3">No product sales available.</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Top 10 Products</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>🏆 Top 10 Best-Selling Products</h2>

        <table border="1" cellpadding="10">
            <tr>
                <th>Product Name</th>
                <th>Quantity Sold</th>
                <th>Sales Revenue</th>
            </tr>
            {rows}
        </table>

        <br>
        <a href="/">Back to Home</a>
    </body>
    </html>
    """
@app.route("/slow_moving")
@role_required("admin", "cashier")
def slow_moving():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            p.product_id,
            p.name,
            p.category,
            p.stock_qty,
            COALESCE(SUM(
                CASE
                    WHEN s.sale_date >= date('now', '-30 days')
                    THEN s.quantity
                    ELSE 0
                END
            ), 0) AS quantity_sold
        FROM products p
        LEFT JOIN sales s
            ON p.product_id = s.product_id
        GROUP BY
            p.product_id,
            p.name,
            p.category,
            p.stock_qty
        HAVING quantity_sold = 0
        ORDER BY p.stock_qty DESC
    """)

    products = cursor.fetchall()
    connection.close()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Slow-Moving Products</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>Slow-Moving Products Report</h2>
        <p>Products with no recorded sales in the last 30 days.</p>

        <table border="1" cellpadding="10">
            <tr>
                <th>Product ID</th>
                <th>Product Name</th>
                <th>Category</th>
                <th>Current Stock</th>
                <th>Quantity Sold in Last 30 Days</th>
            </tr>
    """

    for product in products:
        html += f"""
            <tr>
                <td>{product[0]}</td>
                <td>{product[1]}</td>
                <td>{product[2]}</td>
                <td>{product[3]}</td>
                <td>{product[4]}</td>
            </tr>
        """

    if not products:
        html += """
            <tr>
                <td colspan="5">No slow-moving products found.</td>
            </tr>
        """

    html += """
        </table>
        <br>
        <a href="/dashboard">Back to Dashboard</a>
        <br><br>
        <a href="/products">View Products</a>
    </body>
    </html>
    """

    return html

@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GreenLeaf Grocers</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>

        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>Inventory & Sales Management System</h2>

        <p>Welcome to GreenLeaf Grocers!</p>
        <p>Manage products, track sales, and monitor your business.</p>

        <hr>

        <h3>📦 Inventory Management</h3>
        <a href="/products">View Products</a>
        <br><br>
        <a href="/low_stock">Low Stock Report</a>
        <br><br>
        <a href="/export_products">Export Products</a>

        <hr>

        <h3>💰 Sales Management</h3>
        <a href="/billing">Create Bill</a>
        <br><br>
        <a href="/sales">Sales History</a>

        <hr>

        <h3>📊 Business Reports</h3>
        <a href="/dashboard">Business Dashboard</a>
        <br><br>
        <a href="/daily_sales">Daily Sales Report</a>
        <br><br>
        <a href="/monthly_sales">Monthly Sales Report</a>
        <br><br>
        <a href="/category_sales">Category-wise Sales</a>
        <br><br>
        <a href="/top_products">Top-Selling Products</a>

    </body>
    </html>
    """ 
@app.route("/sales_summary")
def sales_summary():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            product_name,
            SUM(quantity),
            SUM(total_amount)
        FROM sales
        GROUP BY product_name
        ORDER BY SUM(total_amount) DESC
    """)

    sales_data = cursor.fetchall()
    connection.close()

    rows = ""

    for sale in sales_data:
        rows += f"""
        <tr>
            <td>{sale[0]}</td>
            <td>{sale[1]}</td>
            <td>₹{sale[2]:.2f}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sales Summary</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>💰 Product-wise Sales Summary</h2>

        <table>
            <tr>
                <th>Product Name</th>
                <th>Quantity Sold</th>
                <th>Total Revenue</th>
            </tr>
            {rows}
        </table>

        <br>
        <a href="/">Home</a>
        <a href="/dashboard">Dashboard</a>
    </body>
    </html>
    """ 
@app.route("/expiry_alerts")
@role_required("admin", "cashier")
def expiry_alerts():
    import datetime

    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    today = datetime.date.today()
    today_string = today.isoformat()
    future_date = (today + datetime.timedelta(days=15)).isoformat()

    cursor.execute("""
        SELECT product_id, name, category, stock_qty, expiry_date
        FROM products
        WHERE expiry_date IS NOT NULL
          AND DATE(expiry_date) <= DATE(?)
        ORDER BY DATE(expiry_date) ASC
    """, (future_date,))

    products_data = cursor.fetchall()
    connection.close()

    rows = ""

    for product in products_data:
        expiry_date = product[4]

        if expiry_date and expiry_date < today_string:
            status = "Expired"
        elif expiry_date and expiry_date == today_string:
            status = "Expires Today"
        else:
            status = "Expiring Soon"

        rows += f"""
        <tr>
            <td>{product[0]}</td>
            <td>{product[1]}</td>
            <td>{product[2]}</td>
            <td>{product[3]}</td>
            <td>{expiry_date}</td>
            <td>{status}</td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="6">No expired or soon-to-expire products found.</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Expiry Alerts</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>⚠️ Product Expiry Alerts</h2>
        <p>Showing expired products and products expiring within 15 days.</p>

        <table border="1" cellpadding="10">
            <tr>
                <th>Product ID</th>
                <th>Product Name</th>
                <th>Category</th>
                <th>Stock Quantity</th>
                <th>Expiry Date</th>
                <th>Status</th>
            </tr>
            {rows}
        </table>

        <br>
        <a href="/">Back to Home</a>
    </body>
    </html>
    """           
if __name__ == "__main__":
    app.run(debug=True)  