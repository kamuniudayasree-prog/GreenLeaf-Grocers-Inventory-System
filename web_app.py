from flask import Flask, request, redirect
import sqlite3
import csv

app = Flask(__name__)

@app.route("/products")
def products():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM products")
    all_products = cursor.fetchall()

    connection.close()

    html = """
    <link rel="stylesheet" href="/static/style.css">
    <h1>🌿 GreenLeaf Grocers</h1>
    <h2>Product Inventory</h2>
    <a href="/add_product">➕ Add New Product</a>
    <br><br>
    <a href="/export_products">💾 Export Products to Excel</a>
    <br><br>
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

                <a href="/delete_product/{product[0]}"
                   onclick="return confirm('Are you sure you want to delete this product?')">
                   Delete
                </a>
            </td>
        </tr>
        """

    html += """
    </table>
    <br>
    <a href="/">Back to Home</a>
    """

    return html


@app.route("/add_product")
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

        <form action="/save_product" method="POST">
            <p>Product Name:</p>
            <input type="text" name="name" required>

            <p>Category:</p>
            <input type="text" name="category" required>

            <p>Price:</p>
            <input type="number" name="price" step="0.01" min="0.01" required>

            <p>Stock Quantity:</p>
            <input type="number" name="stock_qty" min="0" required>

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
def save_product():
    name = request.form["name"]
    category = request.form["category"]
    price = float(request.form["price"])
    stock_qty = int(request.form["stock_qty"])

    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO products (name, category, price, stock_qty) VALUES (?, ?, ?, ?)",
        (name, category, price, stock_qty)
    )

    connection.commit()
    connection.close()

    return redirect("/products")

@app.route("/delete_product/<int:product_id>")
def delete_product(product_id):
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM products WHERE product_id = ?",
        (product_id,)
    )

    connection.commit()
    connection.close()

    return redirect("/products")
@app.route("/edit_product/<int:product_id>")
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

        <form action="/update_product/{product[0]}" method="POST">
            <p>Product Name:</p>
            <input type="text" name="name" value="{product[1]}" required>

            <p>Category:</p>
            <input type="text" name="category" value="{product[2]}" required>

            <p>Price:</p>
            <input type="number" name="price" value="{product[3]}" step="0.01" min="0.01" required>

            <p>Stock Quantity:</p>
            <input type="number" name="stock_qty" value="{product[4]}" min="0" required>

            <br><br>
            <button type="submit">Save Changes</button>
        </form>

        <a href="/products">Back to Products</a>
    </body>
    </html>
    """  
@app.route("/update_product/<int:product_id>", methods=["POST"])
def update_product(product_id):
    name = request.form["name"]
    category = request.form["category"]
    price = float(request.form["price"])
    stock_qty = int(request.form["stock_qty"])

    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE products
        SET name = ?, category = ?, price = ?, stock_qty = ?
        WHERE product_id = ?
        """,
        (name, category, price, stock_qty, product_id)
    )

    connection.commit()
    connection.close()

    return redirect("/products")

@app.route("/billing")
def billing():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM products WHERE stock_qty > 0")
    products = cursor.fetchall()

    connection.close()

    options = ""

    for product in products:
        options += f"""
        <option value="{product[0]}">
            {product[1]} - ₹{product[3]} (Stock: {product[4]})
        </option>
        """

    return f"""
    <html>
    <head>
        <title>GreenLeaf Billing</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>Sales Billing System</h2>

        <form action="/create_bill" method="POST">
            <p>Select Product:</p>

            <select name="product_id" required>
                {options}
            </select>

            <p>Quantity:</p>
            <input type="number" name="quantity" min="1" required>

            <br><br>
            <button type="submit">Generate Bill</button>
        </form>

        <a href="/products">Back to Products</a>
    </body>
    </html>
    """
@app.route("/create_bill", methods=["POST"])
def create_bill():
    product_id = int(request.form["product_id"])
    quantity = int(request.form["quantity"])

    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT name, price, stock_qty FROM products WHERE product_id = ?",
        (product_id,)
    )

    product = cursor.fetchone()

    if product is None:
        connection.close()
        return "Product not found!"

    name, price, stock_qty = product

    if quantity <= 0:
        connection.close()
        return "Quantity must be greater than zero!"

    if quantity > stock_qty:
        connection.close()
        return f"Insufficient stock! Available stock: {stock_qty}"

    total_amount = price * quantity
    remaining_stock = stock_qty - quantity

    cursor.execute("""
        INSERT INTO sales
        (product_id, product_name, quantity, unit_price, total_amount)
        VALUES (?, ?, ?, ?, ?)
    """, (product_id, name, quantity, price, total_amount))

    cursor.execute(
        "UPDATE products SET stock_qty = ? WHERE product_id = ?",
        (remaining_stock, product_id)
    )

    connection.commit()
    connection.close()

    return f"""
    <html>
    <head>
        <title>GreenLeaf Bill</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>✅ Bill Generated Successfully!</h2>

        <p><b>Product:</b> {name}</p>
        <p><b>Quantity:</b> {quantity}</p>
        <p><b>Price per item:</b> ₹{price:.2f}</p>
        <hr>
        <h2>Total Amount: ₹{total_amount:.2f}</h2>
        <p><b>Remaining Stock:</b> {remaining_stock}</p>

        <a href="/billing">Create Another Bill</a>
        <br><br>
        <a href="/products">View Products</a>
    </body>
    </html>
    """
@app.route("/sales")
def sales():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

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
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    # Total products
    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]

    # Total revenue
    cursor.execute("SELECT SUM(total_amount) FROM sales")
    total_revenue = cursor.fetchone()[0] or 0

    # Total bills
    cursor.execute("SELECT COUNT(*) FROM sales")
    total_bills = cursor.fetchone()[0]

    connection.close()

    return f"""
    <html>
    <head>
        <title>GreenLeaf Dashboard</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <hr>

<h3>📋 Inventory Management</h3>
<a href="/products">View All Products</a>
<br><br>
<a href="/low_stock">Low Stock Report</a>
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
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>Business Dashboard</h2>

        <div class="dashboard-card">
            <h3>🛒 Total Products</h3>
            <h2>{total_products}</h2>
        </div>

        <div class="dashboard-card">
            <h3>💰 Total Revenue</h3>
            <h2>₹{total_revenue:.2f}</h2>
        </div>

        <div class="dashboard-card">
            <h3>🧾 Total Bills</h3>
            <h2>{total_bills}</h2>
        </div>

        <br>
        <a href="/products">Manage Products</a>
        <br><br>
        <a href="/billing">Create Bill</a>
        <br><br>
        <a href="/sales">Sales History</a>
    </body>
    </html>
   """
@app.route("/low_stock")
def low_stock():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT product_id, name, category, price, stock_qty
        FROM products
        WHERE stock_qty <= 10
        ORDER BY stock_qty ASC
    """)

    products = cursor.fetchall()
    connection.close()

    rows = ""

    for product in products:
        rows += f"""
        <tr>
            <td>{product[0]}</td>
            <td>{product[1]}</td>
            <td>{product[2]}</td>
            <td>₹{product[3]:.2f}</td>
            <td>⚠️ {product[4]}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
        <title>Low Stock Report</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>⚠️ Low Stock Products</h2>
        <p>Products with 10 or fewer items remaining.</p>

        <table>
            <tr>
                <th>Product ID</th>
                <th>Product Name</th>
                <th>Category</th>
                <th>Price</th>
                <th>Available Stock</th>
            </tr>
            {rows}
        </table>

        <br>
        <a href="/dashboard">Back to Dashboard</a>
        <br><br>
        <a href="/products">Manage Products</a>
    </body>
    </html>
    """
@app.route("/export_products")
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
@app.route("/category_sales")
def category_sales():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT p.category, SUM(s.total_amount)
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        GROUP BY p.category
        ORDER BY SUM(s.total_amount) DESC
    """)

    categories = cursor.fetchall()
    connection.close()

    rows = ""

    for category in categories:
        rows += f"""
        <tr>
            <td>{category[0]}</td>
            <td>₹{category[1]:.2f}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
        <title>Category Sales Analytics</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>📊 Category-wise Sales</h2>

        <table border="1" cellpadding="10">
            <tr>
                <th>Category</th>
                <th>Total Revenue</th>
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
def daily_sales():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT DATE(sale_date), COUNT(*), SUM(total_amount)
        FROM sales
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

    return f"""
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
    </body>
    </html>
    """
@app.route("/monthly_sales")
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
def top_products():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            product_name,
            SUM(quantity) AS total_sold,
            SUM(total_amount) AS total_revenue
        FROM sales
        GROUP BY product_name
        ORDER BY total_sold DESC
    """)

    products = cursor.fetchall()
    connection.close()

    rows = ""

    for product in products:
        rows += f"""
        <tr>
            <td>{product[0]}</td>
            <td>{product[1]}</td>
            <td>₹{product[2]:.2f}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
        <title>Top-Selling Products</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>🌿 GreenLeaf Grocers</h1>
        <h2>🏆 Top-Selling Products Report</h2>

        <table border="1" cellpadding="10">
            <tr>
                <th>Product Name</th>
                <th>Total Quantity Sold</th>
                <th>Total Revenue</th>
            </tr>
            {rows}
        </table>

        <br>
        <a href="/dashboard">Back to Dashboard</a>
        <br><br>
        <a href="/monthly_sales">Monthly Sales Report</a>
    </body>
    </html>
    """  
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
if __name__ == "__main__":
    app.run(debug=True)  