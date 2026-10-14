import sqlite3


# ADD PRODUCT
def add_product():
    name = input("Enter product name: ")
    category = input("Enter product category: ")
    price = float(input("Enter product price: "))
    stock_qty = int(input("Enter stock quantity: "))

    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO products (name, category, price, stock_qty)
        VALUES (?, ?, ?, ?)
    """, (name, category, price, stock_qty))

    connection.commit()

    if cursor.rowcount > 0:
        print("Product added successfully! ✅")
    else:
        print("This product already exists! ⚠️")

    connection.close()


# VIEW PRODUCTS
def view_products():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    print("\n--- GREENLEAF GROCERS: PRODUCT LIST ---")

    for product in products:
        print(product)

    connection.close()


# UPDATE PRODUCT
def update_product():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    product_id = int(input("Enter product ID to update: "))
    new_price = float(input("Enter new price: "))
    new_stock = int(input("Enter new stock quantity: "))

    cursor.execute("""
        UPDATE products
        SET price = ?, stock_qty = ?
        WHERE product_id = ?
    """, (new_price, new_stock, product_id))

    connection.commit()

    if cursor.rowcount > 0:
        print("Product updated successfully! ✅")
    else:
        print("Product ID not found! ❌")

    connection.close()
# DELETE PRODUCT
def delete_product():
    connection = sqlite3.connect("greenleaf.db")
    cursor = connection.cursor()

    product_id = int(input("Enter product ID to delete: "))

    cursor.execute(
        "DELETE FROM products WHERE product_id = ?",
        (product_id,)
    )

    connection.commit()

    if cursor.rowcount > 0:
        print("Product deleted successfully! ✅")
    else:
        print("Product ID not found! ❌")

    connection.close()

# MAIN MENU
while True:
    print("\n==============================")
    print("      GREENLEAF GROCERS")
    print(" Inventory & Sales Management")
    print("==============================")
    print("1. Add Product")
    print("2. View Products")
    print("3. Update Product")
    print("4. Delete Product")
    print("5. Exit")

    choice = input("Enter your choice: ")

    if choice == "1":
        add_product()

    elif choice == "2":
        view_products()

    elif choice == "3":
        update_product()

    elif choice == "4":
        delete_product()

    elif choice == "5":
        print("Thank you for using GreenLeaf Grocers!")
        break

    else:
        print("Invalid choice! Please try again.")