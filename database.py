import sqlite3

connection = sqlite3.connect("greenleaf.db")
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    stock_qty INTEGER NOT NULL
)
""")

products = [
    ("Rice", "Grains", 60, 100),
    ("Milk", "Dairy", 30, 50),
    ("Bread", "Bakery", 40, 20),
    ("Sugar", "Grains", 45, 80),
    ("Eggs", "Dairy", 7, 120)
]

cursor.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS unique_product_name
ON products(name)
""")

cursor.executemany("""
INSERT OR IGNORE INTO products (name, category, price, stock_qty)
VALUES (?, ?, ?, ?)
""", products)

cursor.execute("SELECT * FROM products")
all_products = cursor.fetchall()

print("\nGREENLEAF GROCERS - PRODUCT LIST")

for product in all_products:
    print(product)

cursor.execute("""
CREATE TABLE IF NOT EXISTS sales (
    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    total_amount REAL NOT NULL,
    sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

connection.commit()

print("Sales table created successfully!")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("TABLES:", cursor.fetchall())

cursor.execute("SELECT COUNT(*) FROM products")
print("TOTAL PRODUCTS:", cursor.fetchone()[0])

cursor.execute("SELECT COUNT(*) FROM sales")
print("TOTAL SALES:", cursor.fetchone()[0])

cursor.execute("PRAGMA table_info(products)")
print("PRODUCT COLUMNS:", cursor.fetchall())

cursor.execute("PRAGMA table_info(sales)")
print("SALES COLUMNS:", cursor.fetchall())

connection.close()
