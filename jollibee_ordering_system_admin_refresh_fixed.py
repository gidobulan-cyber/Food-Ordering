import csv
import random
import sqlite3
from datetime import datetime
from pathlib import Path

print("RUNNING UPDATED JOLLIBEE SYSTEM")
print("FILE LOCATION:", __file__)



DB_NAME = Path(__file__).resolve().parent / "jollibee_orders.db"
ADMIN_PASSWORD = "1234"

MENU = {
    "Chickenjoy Meals": {
        1: ("1pc Chickenjoy with Rice", 99, 10),
        2: ("1pc Chickenjoy with Spaghetti", 145, 12),  
        3: ("2pc Chickenjoy with Rice", 169, 15),
        4: ("Chickenjoy Bucket (6pcs)", 499, 20),
    },
    "Burger Meals": {
        5: ("Yumburger with Fries and Drink", 99, 8),
        6: ("Cheesy Yumburger Meal", 119, 8),
        7: ("Champ Meal", 179, 12),
    },
    "Solo Burgers": {
        8: ("Yumburger", 45, 5),
        9: ("Cheesy Yumburger", 59, 6),
        10: ("Champ Burger", 139, 10),
    },
    "Jolly Spaghetti": {
        11: ("Jolly Spaghetti Solo", 65, 7),
        12: ("Jolly Spaghetti with Drink", 89, 8),
        13: ("Jolly Spaghetti Family Pan", 220, 12),
    },
    "Sides and Drinks": {
        14: ("Regular Fries", 45, 5),
        15: ("Large Fries", 65, 5),
        16: ("Peach Mango Pie", 39, 5),
        17: ("Coke Float", 49, 3),
        18: ("Regular Coke", 35, 2),
    },
}



def connect_db():
    conn = sqlite3.connect(DB_NAME, timeout=15)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def initialize_database():
    with connect_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS menu_categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS menu_items (
            item_id INTEGER PRIMARY KEY,
            category_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            price REAL NOT NULL,
            prep_time INTEGER NOT NULL,
            is_available INTEGER NOT NULL DEFAULT 1,
            stock INTEGER NOT NULL DEFAULT 20,
            FOREIGN KEY(category_id)
                REFERENCES menu_categories(category_id)
        );

        CREATE TABLE IF NOT EXISTS orders (
            order_number INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            order_date TEXT NOT NULL,
            order_type TEXT NOT NULL,
            total REAL NOT NULL,
            payment_method TEXT NOT NULL,
            online_method TEXT NOT NULL DEFAULT 'N/A',
            prep_time INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Awaiting Payment',
            payment_status TEXT NOT NULL DEFAULT 'Pending',
            payment_reference TEXT NOT NULL DEFAULT '',
            confirmation_number INTEGER,
            table_number TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS order_items (
            order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            unit_price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY(order_number)
                REFERENCES orders(order_number) ON DELETE CASCADE,
            FOREIGN KEY(item_id)
                REFERENCES menu_items(item_id)
        );

        CREATE INDEX IF NOT EXISTS idx_orders_date
        ON orders(order_date);

        CREATE INDEX IF NOT EXISTS idx_order_items_order
        ON order_items(order_number);
        """)

        # Upgrade databases created by earlier versions.
        order_columns = [row[1] for row in conn.execute("PRAGMA table_info(orders)")]
        if "payment_status" not in order_columns:
            conn.execute("ALTER TABLE orders ADD COLUMN payment_status TEXT NOT NULL DEFAULT 'Confirmed'")
            # Existing orders were already being processed in the previous version.
        if "payment_reference" not in order_columns:
            conn.execute("ALTER TABLE orders ADD COLUMN payment_reference TEXT NOT NULL DEFAULT ''")
        if "confirmation_number" not in order_columns:
            conn.execute("ALTER TABLE orders ADD COLUMN confirmation_number INTEGER")
        if "table_number" not in order_columns:
            conn.execute("ALTER TABLE orders ADD COLUMN table_number TEXT NOT NULL DEFAULT ''")

        columns = [row[1] for row in conn.execute("PRAGMA table_info(menu_items)")]
        if "stock" not in columns:
            conn.execute("ALTER TABLE menu_items ADD COLUMN stock INTEGER NOT NULL DEFAULT 20")

        for category, items in MENU.items():

            conn.execute("""
                INSERT OR IGNORE INTO menu_categories
                (category_name)
                VALUES (?)
            """, (category,))

            category_id = conn.execute("""
                SELECT category_id
                FROM menu_categories
                WHERE category_name = ?
            """, (category,)).fetchone()[0]

            for item_id, (name, price, prep_time) in items.items():

                conn.execute("""
                    INSERT OR IGNORE INTO menu_items
                    (item_id, category_id, item_name, price, prep_time)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    item_id,
                    category_id,
                    name,
                    price,
                    prep_time
                ))




def main_menu():

    while True:

        print("\n" + "=" * 50)
        print("              WELCOME TO JOLLIBEE!")
        print("                ORDERING SYSTEM")
        print("=" * 50)

        print("1. Admin")
        print("2. User / Customer")
        print("0. Exit System")

        choice = input("\nSelect Menu: ")

        if choice == "1":
            admin_login()

        elif choice == "2":
            user_menu()

        elif choice == "0":
            print("\nThank you for using Jollibee Ordering System!")
            break

        else:
            print("\nInvalid selection. Please try again.")




def admin_login():

    print("\n" + "=" * 50)
    print("                  ADMIN LOGIN")
    print("=" * 50)

    password = input("Enter Admin Password: ")

    if password == ADMIN_PASSWORD:
        print("\nLogin Successful!")
        admin_menu()

    else:
        print("\nIncorrect Password!")
        print("Access Denied.")


def admin_menu():

    while True:

        print("\n" + "=" * 50)
        print("                  ADMIN MENU")
        print("=" * 50)

        print("1. View All Orders")
        print("2. View Order Details")
        print("3. Update Order Status")
        print("4. Admin Dashboard")
        print("0. Logout")

        choice = input("\nSelect Option: ")

        if choice == "1":
            view_all_orders()

        elif choice == "2":
            view_order_details()

        elif choice == "3":
            update_order_status()

        elif choice == "4":
            admin_dashboard()

        elif choice == "0":
            print("\nAdmin Logged Out.")
            break

        else:
            print("\nInvalid selection.")



def admin_dashboard():

    with connect_db() as conn:

        summary = conn.execute("""
            SELECT
                COUNT(*),
                COALESCE(SUM(CASE WHEN payment_status='Confirmed' THEN total ELSE 0 END), 0),
                COALESCE(SUM(
                    CASE
                        WHEN status != 'Completed' THEN 1
                        ELSE 0
                    END
                ), 0),
                COALESCE(SUM(
                    CASE
                        WHEN status = 'Completed' THEN 1
                        ELSE 0
                    END
                ), 0)
            FROM orders
        """).fetchone()

        status_rows = conn.execute("""
            SELECT status, COUNT(*)
            FROM orders
            GROUP BY status
            ORDER BY status
        """).fetchall()

        recent_orders = conn.execute("""
            SELECT order_number, customer_name,
                   total, status, order_date
            FROM orders
            ORDER BY order_date DESC
            LIMIT 5
        """).fetchall()

    total_orders = summary[0]
    total_sales = summary[1]
    pending_orders = summary[2]
    completed_orders = summary[3]

    print("\n" + "=" * 65)
    print("                     ADMIN DASHBOARD")
    print("=" * 65)

    print(f"Total Orders       : {total_orders}")
    print(f"Total Sales        : PHP {total_sales:,.2f}")
    print(f"Pending Orders     : {pending_orders}")
    print(f"Completed Orders   : {completed_orders}")

    print("\nORDER STATUS SUMMARY")
    print("-" * 65)

    if status_rows:

        for status, count in status_rows:
            print(f"{status:<25} {count:>5} order(s)")

    else:
        print("No orders have been placed yet.")

    print("\nFIVE MOST RECENT ORDERS")
    print("-" * 65)

    if recent_orders:

        print(
            f"{'ORDER NO.':<12}"
            f"{'CUSTOMER':<20}"
            f"{'TOTAL':<15}"
            f"{'STATUS'}"
        )

        print("-" * 65)

        for number, customer, total, status, order_date in recent_orders:

            print(
                f"{number:<12}"
                f"{customer[:19]:<20}"
                f"PHP {total:<10.2f}"
                f"{status}"
            )

            print(f"  Date: {order_date}")

    else:
        print("No recent orders to display.")

    print("=" * 65)

    input("\nPress Enter to return to Admin Menu...")



def view_all_orders():

    with connect_db() as conn:

        rows = conn.execute("""
            SELECT order_number, customer_name,
                   order_type, total, payment_method,
                   online_method, prep_time, status
            FROM orders
            ORDER BY order_date DESC
        """).fetchall()

    print("\n" + "=" * 75)
    print("                         ALL CUSTOMER ORDERS")
    print("=" * 75)

    if not rows:
        print("No orders available yet.")
        return

    for order in rows:

        number = order[0]
        customer = order[1]
        order_type = order[2]
        total = order[3]
        payment = order[4]
        online = order[5]
        prep = order[6]
        status = order[7]

        print(f"\nOrder Number : {number}")
        print(f"Customer     : {customer}")
        print(f"Order Type   : {order_type}")
        print(f"Total Amount : PHP {total:.2f}")

        if payment == "Online":
            print(f"Payment      : {payment} ({online})")
        else:
            print(f"Payment      : {payment}")

        print(f"Prep Time    : {prep} minutes")
        print(f"Status       : {status}")

        print("-" * 75)



def view_order_details():

    try:
        number = int(input("\nEnter Order Number: "))

    except ValueError:
        print("Please enter a valid order number.")
        return

    with connect_db() as conn:

        order = conn.execute("""
            SELECT *
            FROM orders
            WHERE order_number = ?
        """, (number,)).fetchone()

        items = conn.execute("""
            SELECT item_name, unit_price, quantity, subtotal
            FROM order_items
            WHERE order_number = ?
        """, (number,)).fetchall()

    if not order:
        print("\nOrder number not found.")
        return

    print("\n" + "=" * 60)
    print("                    ORDER DETAILS")
    print("=" * 60)

    print("Order Number :", order[0])
    print("Customer     :", order[1])
    print("Date         :", order[2])
    print("Order Type   :", order[3])

    print("\nORDERED ITEMS")
    print("-" * 60)

    for name, price, quantity, subtotal in items:

        print(f"Food       : {name}")
        print(f"Price      : PHP {price:.2f}")
        print(f"Quantity   : {quantity}")
        print(f"Subtotal   : PHP {subtotal:.2f}")

        print("-" * 60)

    print(f"Total Amount : PHP {order[4]:.2f}")
    print("Payment      :", order[5])

    if order[5] == "Online":
        print("Online Method:", order[6])

    print("Prep Time    :", order[7], "minutes")
    print("Order Status :", order[8])

    print("=" * 60)



def update_order_status():

    try:
        number = int(input("\nEnter Order Number: "))

    except ValueError:
        print("Invalid order number.")
        return

    order = get_order(number)

    if not order:
        print("\nOrder not found.")
        return

    print("\nCustomer :", order[1])
    print("Current Status :", order[8])

    print("\n1. Preparing")
    print("2. Ready for Pickup / Serving")
    print("3. Completed")

    choice = input("\nSelect New Status: ")

    statuses = {
        "1": "Preparing",
        "2": "Ready",
        "3": "Completed"
    }

    if choice not in statuses:
        print("\nInvalid selection.")
        return

    with connect_db() as conn:

        conn.execute("""
            UPDATE orders
            SET status = ?
            WHERE order_number = ?
        """, (statuses[choice], number))

    print("\nOrder status successfully updated!")
    print("New Status:", statuses[choice])


def get_order(order_number):

    with connect_db() as conn:

        return conn.execute("""
            SELECT *
            FROM orders
            WHERE order_number = ?
        """, (order_number,)).fetchone()



def user_menu():

    print("\n" + "=" * 50)
    print("               CUSTOMER ORDERING")
    print("=" * 50)

    customer = input("\nEnter Customer Name: ").strip()

    if not customer:
        print("Customer name cannot be empty.")
        return

    print("\nWelcome,", customer + "!")

    order_items = []
    total = 0
    prep_times = []

    while True:

        categories = get_categories()

        print("\n" + "=" * 50)
        print("                  FOOD MENU")
        print("=" * 50)

        for index, (_, category_name) in enumerate(categories, 1):
            print(f"{index}. {category_name}")

        print("0. Finish Order")

        try:
            category_choice = int(input("\nSelect Food Category: "))

        except ValueError:
            print("Invalid input. Please enter a number.")
            continue

        if category_choice == 0:

            if not order_items:
                print("Please select at least one food item.")
                continue

            break

        if not 1 <= category_choice <= len(categories):
            print("Invalid category.")
            continue

        category_id, category_name = categories[category_choice - 1]

        items = get_items(category_id)

        print("\n" + "-" * 50)
        print(category_name.upper())
        print("-" * 50)

        for item_id, name, price, prep_time in items:
            print(f"{item_id}. {name:35} PHP {price:.2f}")

        try:
            food_choice = int(input("\nSelect Food Number: "))

            selected = next(
                (item for item in items if item[0] == food_choice),
                None
            )

            if selected is None:
                print("Invalid food number.")
                continue

            quantity = int(input("Enter Quantity: "))

            if quantity <= 0:
                print("Quantity must be greater than zero.")
                continue

        except ValueError:
            print("Invalid input. Please enter a number.")
            continue

        item_id, food_name, price, prep_time = selected

        subtotal = price * quantity

        order_items.append({
            "item_id": item_id,
            "name": food_name,
            "price": price,
            "quantity": quantity,
            "subtotal": subtotal
        })

        total += subtotal
        prep_times.append(prep_time)

        print("\nSuccessfully Added to Order!")
        print("Food:", food_name)
        print("Quantity:", quantity)
        print(f"Subtotal: PHP {subtotal:.2f}")
        print(f"Current Total: PHP {total:.2f}")

    

    print("\n" + "=" * 50)
    print("                  ORDER TYPE")
    print("=" * 50)

    print("1. Dine In")
    print("2. Takeout")

    while True:

        order_choice = input("\nSelect Order Type: ")

        if order_choice == "1":
            order_type = "Dine In"
            break

        elif order_choice == "2":
            order_type = "Takeout"
            break

        else:
            print("Invalid selection.")

    

    print("\n" + "=" * 50)
    print("                PAYMENT METHOD")
    print("=" * 50)

    print("1. Cash")
    print("2. Online Payment")

    while True:

        payment_choice = input("\nSelect Payment Method: ")

        if payment_choice == "1":

            payment_method = "Cash"
            online_method = "N/A"

            print("\nPlease proceed to the cashier.")
            break

        elif payment_choice == "2":

            payment_method = "Online"

            print("\n1. GCash")
            print("2. GoTyme")

            while True:

                online_choice = input("\nSelect Online Payment: ")

                if online_choice == "1":
                    online_method = "GCash"
                    break

                elif online_choice == "2":
                    online_method = "GoTyme"
                    break

                else:
                    print("Invalid selection.")

            print("\nSelected Payment:", online_method)
            print("Payment is not automatically verified.")

            break

        else:
            print("Invalid payment method.")

    

    prep_time = max(prep_times) + 5

    with connect_db() as conn:

        while True:

            order_number = random.randint(1000, 9999)

            existing_order = conn.execute("""
                SELECT 1
                FROM orders
                WHERE order_number = ?
            """, (order_number,)).fetchone()

            if not existing_order:
                break

        order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute("""
            INSERT INTO orders
            (order_number, customer_name, order_date,
             order_type, total, payment_method,
             online_method, prep_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_number,
            customer,
            order_date,
            order_type,
            total,
            payment_method,
            online_method,
            prep_time,
            "Preparing"
        ))

        for item in order_items:

            conn.execute("""
                INSERT INTO order_items
                (order_number, item_id, item_name,
                 unit_price, quantity, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                order_number,
                item["item_id"],
                item["name"],
                item["price"],
                item["quantity"],
                item["subtotal"]
            ))

    

    print("\n\n" + "=" * 60)
    print("                    JOLLIBEE")
    print("                  ORDER RECEIPT")
    print("=" * 60)

    print("Customer Name :", customer)
    print("Order Number  :", order_number)
    print("Order Type    :", order_type)
    print("Date          :", order_date)

    print("-" * 60)
    print(f"{'ITEM':32} {'QTY':5} {'AMOUNT':10}")
    print("-" * 60)

    for item in order_items:

        print(
            f"{item['name'][:31]:32} "
            f"{item['quantity']:<5} "
            f"{item['subtotal']:>10.2f}"
        )

    print("-" * 60)

    print(f"TOTAL AMOUNT: PHP {total:.2f}")
    print("Payment Method :", payment_method)

    if payment_method == "Online":
        print("Online Service :", online_method)

    print("Estimated Prep :", prep_time, "minutes")

    print("=" * 60)
    print("             THANK YOU FOR ORDERING!")
    print("                  ENJOY YOUR MEAL!")
    print("=" * 60)

    # ======================================
    #              ORDER REMINDER
    # ======================================

    print("\nORDER REMINDER")
    print("-" * 60)

    print("Your Order Number:", order_number)
    print("Estimated Preparation:", prep_time, "minutes")

    if order_type == "Dine In":
        print("Please wait for your order number to be called.")

    else:
        print(
            "Please wait for your order number "
            "at the takeout / pickup counter."
        )

    print("Your order has been saved to the database.")




def get_categories():

    with connect_db() as conn:

        return conn.execute("""
            SELECT category_id, category_name
            FROM menu_categories
            ORDER BY category_id
        """).fetchall()


def get_items(category_id):

    with connect_db() as conn:

        return conn.execute("""
            SELECT item_id, item_name, price, prep_time
            FROM menu_items
            WHERE category_id = ?
            AND is_available = 1
            ORDER BY item_id
        """, (category_id,)).fetchall()




import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog


class JollibeeGUI:
    PURPLE = "#C719D7"
    BLUE = "#2C4CFF"
    CREAM = "#FFF8E7"
    DARK = "#292929"

    # Colors used throughout the interface
    RED = "#D71920"
    YELLOW = "#FFD400"

    def __init__(self, root):
        self.root = root
        self.root.title("Jollibee Ordering System")
        self.root.geometry("1440x900")
        self.root.minsize(1100, 720)
        self.root.configure(bg=self.CREAM)
        self.cart = []
        self.customer_name = tk.StringVar()
        self.category_var = tk.StringVar()
        self.quantity_var = tk.StringVar(value="1")
        self.order_type_var = tk.StringVar(value="Dine In")
        self.payment_var = tk.StringVar(value="Cash")
        self.online_var = tk.StringVar(value="GCash")
        self.table_number_var = tk.StringVar()
        self._refresh_job = None
        self.build_home()

    def clear(self):
        if self._refresh_job is not None:
            try:
                self.root.after_cancel(self._refresh_job)
            except tk.TclError:
                pass
            self._refresh_job = None
        for widget in self.root.winfo_children():
            widget.destroy()

    def schedule_screen_refresh(self, screen, interval_ms=2000):
        """Refresh the currently open data screen every 2 seconds."""
        if self._refresh_job is not None:
            try:
                self.root.after_cancel(self._refresh_job)
            except tk.TclError:
                pass
            self._refresh_job = None

        def refresh_if_still_open():
            self._refresh_job = None
            try:
                if screen == "customer" and hasattr(self, "menu_tree") and self.menu_tree.winfo_exists():
                    self.load_gui_items()
                elif screen == "admin" and hasattr(self, "orders_tree") and self.orders_tree.winfo_exists():
                    self.refresh_admin()
                elif screen == "inventory" and hasattr(self, "inventory_tree") and self.inventory_tree.winfo_exists():
                    self.refresh_inventory()
                else:
                    return
                self._refresh_job = self.root.after(interval_ms, refresh_if_still_open)
            except tk.TclError:
                self._refresh_job = None

        self._refresh_job = self.root.after(interval_ms, refresh_if_still_open)

    def header(self, title, subtitle=None):
        top = tk.Frame(self.root, bg=self.RED, height=90)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text=title, bg=self.RED, fg="white",
                 font=("Arial", 21, "bold")).pack(pady=(15, 2))
        if subtitle:
            tk.Label(top, text=subtitle, bg=self.RED, fg=self.YELLOW,
                     font=("Arial", 10)).pack()

    def styled_button(self, parent, text, command, color=None, width=18):
        return tk.Button(parent, text=text, command=command,
                         bg=color or self.RED, fg="white",
                         activebackground=self.YELLOW, activeforeground=self.DARK,
                         font=("Arial", 10, "bold"), relief="flat",
                         padx=10, pady=8, cursor="hand2", width=width)

    def build_home(self):
        self.clear()
        self.header("WELCOME TO JOLLIBEE!", "ORDERING SYSTEM")
        body = tk.Frame(self.root, bg=self.CREAM)
        body.pack(expand=True)
        tk.Label(body, text="What would you like to do?",
                 bg=self.CREAM, fg=self.DARK,
                 font=("Arial", 18, "bold")).pack(pady=28)
        self.styled_button(body, "CUSTOMER ORDER", self.build_customer,
                           width=25).pack(pady=10)
        self.styled_button(body, "ADMIN", self.admin_login,
                           color=self.DARK, width=25).pack(pady=10)
        self.styled_button(body, "EXIT", self.root.destroy,
                           color="#666666", width=25).pack(pady=10)
        tk.Label(self.root, text="Jollibee Ordering System • SQLite Database",
                 bg=self.CREAM, fg="#777777").pack(side="bottom", pady=12)

    def build_customer(self):
        self.clear()
        self.cart = []
        self.customer_name.set("")
        self.quantity_var.set("1")
        self.order_type_var.set("Dine In")
        self.payment_var.set("Cash")
        self.online_var.set("GCash")
        self.table_number_var.set("")
        self.header("CUSTOMER ORDERING", "Choose your favorite meals")
        # Use the available display size so the checkout and navigation controls
        # remain visible even on smaller laptop screens.
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(1440, max(980, screen_w - 80))
        win_h = min(900, max(680, screen_h - 100))
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.minsize(900, 620)
        style = ttk.Style(self.root)
        style.configure("Customer.Treeview", font=("Arial", 12), rowheight=32)
        style.configure("Customer.Treeview.Heading", font=("Arial", 12, "bold"))
        style.configure("Customer.TCombobox", font=("Arial", 13))
        # High-contrast category selector so it is easy to notice and read.
        style.configure("CustomerCategory.TCombobox", font=("Arial", 15, "bold"),
                        padding=(10, 9), foreground="#B5121B",
                        fieldbackground="#FFF1C7", background="#F4B400",
                        arrowcolor="#B5121B", bordercolor="#D71920",
                        lightcolor="#D71920", darkcolor="#D71920")
        style.map("CustomerCategory.TCombobox",
                  fieldbackground=[("readonly", "#FFF1C7"), ("!disabled", "#FFF1C7")],
                  foreground=[("readonly", "#B5121B")],
                  selectbackground=[("readonly", "#D71920")],
                  selectforeground=[("readonly", "#FFFFFF")],
                  background=[("active", "#F4B400")])
        style.configure("Checkout.TCombobox", font=("Arial", 13), padding=6)
        outer = tk.Frame(self.root, bg=self.CREAM, padx=24, pady=16)
        outer.pack(fill="both", expand=True)

        top = tk.Frame(outer, bg=self.CREAM)
        top.pack(fill="x", pady=(0, 10))
        tk.Label(top, text="Customer name:", bg=self.CREAM,
                 font=("Arial", 13, "bold")).pack(side="left")
        self.customer_entry = tk.Entry(top, textvariable=self.customer_name,
                                       font=("Arial", 13), width=34)
        self.customer_entry.pack(side="left", padx=8)

        content = tk.Frame(outer, bg=self.CREAM)
        content.pack(fill="both", expand=True)

        left = tk.LabelFrame(content, text="FOOD MENU", bg="white",
                             font=("Arial", 13, "bold"), padx=14, pady=14)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right = tk.LabelFrame(content, text="YOUR CART", bg="white",
                              font=("Arial", 13, "bold"), padx=14, pady=14)
        right.pack(side="right", fill="both", expand=True)

        categories = get_categories()
        names = [row[1] for row in categories]
        category_bar = tk.Frame(left, bg="#D71920", padx=10, pady=8)
        category_bar.pack(fill="x", pady=(0, 8))
        tk.Label(category_bar, text="CHOOSE FOOD CATEGORY", bg="#D71920", fg="white",
                 font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 5))
        self.category_box = ttk.Combobox(category_bar, values=names, state="readonly",
                                         textvariable=self.category_var,
                                         style="CustomerCategory.TCombobox")
        self.category_box.pack(fill="x")
        self.category_box.bind("<<ComboboxSelected>>", self.on_menu_category_change)
        if names:
            self.category_box.current(0)

        self.selected_menu_item_ids = set()
        self.menu_tree = ttk.Treeview(
            left, columns=("id", "name", "price", "prep", "stock", "status"),
            show="tree headings", height=10, selectmode="browse",
            style="Customer.Treeview"
        )
        self.menu_tree.heading("#0", text="Select")
        self.menu_tree.column("#0", width=52, minwidth=52, stretch=False, anchor="center")
        for col, label, width in [
            ("id", "ID", 48), ("name", "Food Item", 260),
            ("price", "Price", 115), ("prep", "Prep", 75),
            ("stock", "Stock", 75), ("status", "Status", 115)
        ]:
            self.menu_tree.heading(col, text=label)
            self.menu_tree.column(col, width=width, anchor="w")
        self.menu_tree.bind("<Button-1>", self.toggle_menu_checkbox)
        self.menu_tree.pack(fill="both", expand=True)

        addrow = tk.Frame(left, bg="white")
        addrow.pack(fill="x", pady=8)
        tk.Label(addrow, text="Quantity:", bg="white",
                 font=("Arial", 13, "bold")).pack(side="left")
        tk.Spinbox(addrow, from_=1, to=99, width=7, font=("Arial", 14),
                   justify="center", textvariable=self.quantity_var,
                   relief="solid", bd=1).pack(side="left", padx=8, ipady=5)
        add_button = self.styled_button(addrow, "ADD TO CART", self.add_to_cart,
                                        width=17)
        add_button.configure(font=("Arial", 11, "bold"), padx=14, pady=10)
        add_button.pack(side="right")

        self.cart_tree = ttk.Treeview(right, columns=("name", "qty", "subtotal"),
                                      show="headings", height=10, style="Customer.Treeview")
        for col, label, width in [
            ("name", "Item", 290), ("qty", "Qty", 65), ("subtotal", "Amount", 125)
        ]:
            self.cart_tree.heading(col, text=label)
            self.cart_tree.column(col, width=width, anchor="w")
        self.cart_tree.pack(fill="both", expand=True)

        self.total_label = tk.Label(right, text="TOTAL: PHP 0.00",
                                    bg="white", fg=self.RED,
                                    font=("Arial", 16, "bold"))
        self.total_label.pack(anchor="e", pady=10)

        checkout = tk.LabelFrame(outer, text="CHECKOUT & PAYMENT",
                                 bg=self.CREAM, fg=self.RED,
                                 font=("Arial", 13, "bold"), padx=12, pady=10)
        checkout.pack(fill="x", pady=(8, 5))
        checkout.pack_propagate(True)
        options = tk.Frame(checkout, bg=self.CREAM)
        options.pack(fill="x")
        tk.Label(options, text="Order type:", bg=self.CREAM,
                 font=("Arial", 12, "bold")).pack(side="left")
        self.order_type_box = ttk.Combobox(
            options, textvariable=self.order_type_var,
            values=["Dine In", "Takeout"], state="readonly", width=13,
            style="Checkout.TCombobox"
        )
        self.order_type_box.pack(side="left", padx=5)
        tk.Label(options, text="Payment:", bg=self.CREAM,
                 font=("Arial", 12, "bold")).pack(side="left", padx=(12, 0))
        self.payment_box = ttk.Combobox(
            options, textvariable=self.payment_var,
            values=["Cash", "Online"], state="readonly", width=12,
            style="Checkout.TCombobox"
        )
        self.payment_box.pack(side="left", padx=5)
        self.payment_box.bind("<<ComboboxSelected>>", self.toggle_online_payment)
        self.online_payment_frame = tk.Frame(options, bg=self.CREAM)
        tk.Label(self.online_payment_frame, text="Online method:",
                 bg=self.CREAM).pack(side="left", padx=(8, 0))
        self.online_box = ttk.Combobox(
            self.online_payment_frame, textvariable=self.online_var,
            values=["GCash", "GoTyme"], state="readonly", width=12,
            style="Checkout.TCombobox"
        )
        self.online_box.pack(side="left", padx=5)
        self.toggle_online_payment()

        buttons = tk.Frame(outer, bg=self.CREAM)
        buttons.pack(fill="x", pady=(4, 10), side="bottom")
        self.styled_button(buttons, "BACK TO MENU", self.build_home,
                           color="#666666", width=16).pack(side="left", padx=(0, 8))
        self.styled_button(buttons, "UPDATE QTY", self.update_cart_quantity,
                           color="#176B87", width=13).pack(side="left")
        self.styled_button(buttons, "REMOVE SELECTED", self.remove_cart_item,
                           color=self.DARK, width=18).pack(side="left", padx=6)
        place_order_button = self.styled_button(
            buttons, "CHECK OUT / PLACE ORDER", self.place_order,
            color="#25833B", width=25
        )
        place_order_button.configure(font=("Arial", 12, "bold"), padx=20, pady=12)
        place_order_button.pack(side="right")

        self.load_gui_items()
        self.schedule_screen_refresh("customer")

    def toggle_online_payment(self, event=None):
        """Show GCash/GoTyme choices only when Online is selected."""
        if not hasattr(self, "online_payment_frame"):
            return
        if self.payment_var.get() == "Online":
            self.online_payment_frame.pack(side="left")
        else:
            self.online_payment_frame.pack_forget()

    def on_menu_category_change(self, event=None):
        # A category change starts a fresh selection to avoid hidden checked items.
        self.selected_menu_item_ids.clear()
        self.load_gui_items()

    def toggle_menu_checkbox(self, event):
        if self.menu_tree.identify_region(event.x, event.y) != "tree":
            return
        iid = self.menu_tree.identify_row(event.y)
        if not iid:
            return "break"
        values = self.menu_tree.item(iid, "values")
        if not values:
            return "break"
        try:
            item_id = int(values[0])
        except (ValueError, TypeError, IndexError):
            return "break"

        if item_id in self.selected_menu_item_ids:
            self.selected_menu_item_ids.remove(item_id)
        else:
            # Reject sold-out items immediately when the customer clicks their checkbox.
            with connect_db() as conn:
                stock_row = conn.execute(
                    "SELECT item_name, stock FROM menu_items WHERE item_id=? AND is_available=1",
                    (item_id,)
                ).fetchone()
            if not stock_row:
                messagebox.showerror(
                    "Item Unavailable",
                    "This menu item is no longer available. The menu will be refreshed."
                )
                self.load_gui_items()
                return "break"
            if stock_row[1] <= 0:
                messagebox.showerror(
                    "Out of Stock",
                    f"Sorry! {stock_row[0]} is currently SOLD OUT. Please select another item."
                )
                self.load_gui_items()
                return "break"
            self.selected_menu_item_ids.add(item_id)
        self.menu_tree.item(
            iid, text="☑" if item_id in self.selected_menu_item_ids else "☐"
        )
        return "break"

    def load_gui_items(self, event=None):
        if not hasattr(self, "menu_tree") or not self.menu_tree.winfo_exists():
            return
        categories = get_categories()
        category_names = [row[1] for row in categories]
        if hasattr(self, "category_box") and self.category_box.winfo_exists():
            self.category_box.configure(values=category_names)
        current_category = self.category_var.get()
        if current_category not in category_names:
            current_category = category_names[0] if category_names else ""
            self.category_var.set(current_category)
        for row in self.menu_tree.get_children():
            self.menu_tree.delete(row)
        category = self.category_var.get()
        match = next((r for r in categories if r[1] == category), None)
        if not match:
            return
        with connect_db() as conn:
            items = conn.execute("""
                SELECT item_id, item_name, price, prep_time, stock
                FROM menu_items
                WHERE category_id = ? AND is_available = 1
                ORDER BY item_id
            """, (match[0],)).fetchall()
        visible_ids = {item[0] for item in items}
        self.selected_menu_item_ids.intersection_update(visible_ids)
        for item_id, name, price, prep, stock in items:
            status = "SOLD OUT" if stock <= 0 else "AVAILABLE"
            self.menu_tree.insert(
                "", "end", iid=str(item_id),
                text="☑" if item_id in self.selected_menu_item_ids else "☐",
                values=(item_id, name, f"PHP {price:.2f}", prep, stock, status),
                tags=("soldout",) if stock <= 0 else ()
            )
        self.menu_tree.tag_configure("soldout", foreground="#D71920")

    def add_to_cart(self):
        selected = sorted(self.selected_menu_item_ids)
        if not selected:
            messagebox.showwarning(
                "Select menu items",
                "Click the checkbox beside each food item you want to add."
            )
            return
        try:
            quantity = int(self.quantity_var.get())
            if quantity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid quantity", "Enter a quantity greater than zero.")
            return

        # Validate all selected items first so a partial selection is not added by accident.
        selected_items = []
        for item_id in selected:
            with connect_db() as conn:
                row = conn.execute("""
                    SELECT item_name, price, prep_time, stock
                    FROM menu_items
                    WHERE item_id=? AND is_available=1
                """, (item_id,)).fetchone()

            if not row:
                messagebox.showerror(
                    "Unavailable",
                    f"Menu item #{item_id} is no longer available. The menu will be refreshed."
                )
                self.load_gui_items()
                return

            name, price, prep, stock = row
            if stock <= 0:
                messagebox.showerror("Out of Stock", f"Sorry! {name} is SOLD OUT and cannot be ordered. Please select another item.")
                self.load_gui_items()
                return

            already_in_cart = sum(
                item["quantity"] for item in self.cart if item["item_id"] == item_id
            )
            if already_in_cart + quantity > stock:
                messagebox.showwarning(
                    "Not enough stock",
                    f"Only {stock - already_in_cart} more unit(s) of {name} can be added."
                )
                return

            selected_items.append({
                "item_id": item_id,
                "name": name,
                "price": price,
                "quantity": quantity,
                "subtotal": price * quantity,
                "prep_time": prep
            })

        # Merge repeated selections into one cart line for easier cashier-style review.
        for new_item in selected_items:
            existing = next(
                (item for item in self.cart if item["item_id"] == new_item["item_id"]),
                None
            )
            if existing:
                existing["quantity"] += new_item["quantity"]
                existing["subtotal"] = existing["price"] * existing["quantity"]
            else:
                self.cart.append(new_item)
        self.selected_menu_item_ids.clear()
        self.load_gui_items()
        self.refresh_cart()

    def refresh_cart(self):
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        for index, item in enumerate(self.cart):
            self.cart_tree.insert("", "end", iid=str(index),
                                  values=(item["name"], item["quantity"],
                                          f"PHP {item['subtotal']:.2f}"))
        total = sum(item["subtotal"] for item in self.cart)
        self.total_label.config(text=f"TOTAL: PHP {total:,.2f}")

    def remove_cart_item(self):
        selected = self.cart_tree.selection()
        if not selected:
            return
        del self.cart[int(selected[0])]
        self.refresh_cart()

    def update_cart_quantity(self):
        selected = self.cart_tree.selection()
        if not selected:
            messagebox.showwarning("Select cart item", "Select an item in your cart first.")
            return
        index = int(selected[0])
        item = self.cart[index]
        dialog = tk.Toplevel(self.root)
        dialog.title("Update Item Quantity")
        dialog.configure(bg=self.CREAM)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        tk.Label(dialog, text=item["name"], bg=self.CREAM,
                 font=("Arial", 11, "bold")).pack(padx=20, pady=(18, 8))
        tk.Label(dialog, text="New quantity:", bg=self.CREAM).pack()
        quantity_entry = tk.Entry(dialog, width=12, justify="center")
        quantity_entry.insert(0, str(item["quantity"]))
        quantity_entry.pack(pady=8)
        quantity_entry.focus_set()

        def save():
            try:
                quantity = int(quantity_entry.get())
                if quantity <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid quantity", "Enter a whole number greater than zero.", parent=dialog)
                return
            with connect_db() as conn:
                row = conn.execute(
                    "SELECT stock FROM menu_items WHERE item_id=? AND is_available=1",
                    (item["item_id"],)
                ).fetchone()
            if not row or quantity > row[0]:
                messagebox.showwarning(
                    "Insufficient stock",
                    f"Only {row[0] if row else 0} unit(s) are currently available.",
                    parent=dialog
                )
                return
            item["quantity"] = quantity
            item["subtotal"] = item["price"] * quantity
            dialog.destroy()
            self.refresh_cart()

        self.styled_button(dialog, "SAVE QUANTITY", save, width=18).pack(pady=14)
        quantity_entry.bind("<Return>", lambda event: save())

    def place_order(self):
        customer = self.customer_name.get().strip()
        if not customer:
            messagebox.showwarning("Customer name", "Please enter the customer name.")
            return
        if not self.cart:
            messagebox.showwarning("Empty cart", "Please add at least one item.")
            return

        # Re-read live menu details at checkout. This prevents a stale cart price
        # or an item that has since been disabled from being saved to an order.
        try:
            with connect_db() as conn:
                for item in self.cart:
                    live = conn.execute(
                        "SELECT item_name, price, prep_time, stock, is_available "
                        "FROM menu_items WHERE item_id=?",
                        (item["item_id"],)
                    ).fetchone()
                    if not live or not live[4]:
                        raise ValueError(f"{item['name']} is no longer available.")
                    if live[3] < item["quantity"]:
                        raise ValueError(
                            f"Not enough stock for {live[0]}. Available: {live[3]}."
                        )
                    item["name"], item["price"], item["prep_time"] = live[0], live[1], live[2]
                    item["subtotal"] = item["price"] * item["quantity"]
        except (sqlite3.Error, ValueError) as exc:
            messagebox.showerror("Please review your cart", str(exc))
            self.load_gui_items()
            self.refresh_cart()
            return

        total = sum(item["subtotal"] for item in self.cart)
        prep_time = max(item["prep_time"] for item in self.cart) + 5
        order_type = self.order_type_var.get()
        # Table numbers are not collected in the customer interface.
        table_number = ""
        payment = self.payment_var.get()
        online = self.online_var.get() if payment == "Online" else "N/A"
        order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with connect_db() as conn:
                while True:
                    number = random.randint(1000, 9999)
                    if not conn.execute("SELECT 1 FROM orders WHERE order_number=?",
                                        (number,)).fetchone():
                        break

                used_codes = {
                    row[0] for row in conn.execute(
                        "SELECT confirmation_number FROM orders "
                        "WHERE status NOT IN ('Completed', 'Cancelled') "
                        "AND confirmation_number IS NOT NULL"
                    ).fetchall()
                }
                available_codes = [n for n in range(1, 51) if n not in used_codes]
                if not available_codes:
                    raise ValueError(
                        "All confirmation numbers (1–50) are currently in use. "
                        "Complete or cancel an existing order before accepting another."
                    )
                confirmation_number = random.choice(available_codes)

                conn.execute("""
                    INSERT INTO orders
                    (order_number, customer_name, order_date, order_type, total,
                     payment_method, online_method, prep_time, status,
                     payment_status, payment_reference, confirmation_number, table_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Awaiting Payment', 'Pending', '', ?, ?)
                """, (number, customer, order_date, order_type, total,
                      payment, online, prep_time, confirmation_number, table_number))

                # Reserve stock while the payment is pending.
                for item in self.cart:
                    current = conn.execute(
                        "SELECT stock FROM menu_items WHERE item_id=?",
                        (item["item_id"],)
                    ).fetchone()
                    if not current or current[0] < item["quantity"]:
                        raise ValueError(
                            f"Not enough stock for {item['name']}. "
                            f"Available: {current[0] if current else 0}."
                        )
                    conn.execute(
                        "UPDATE menu_items SET stock = stock - ? WHERE item_id=?",
                        (item["quantity"], item["item_id"])
                    )
                    conn.execute("""
                        INSERT INTO order_items
                        (order_number, item_id, item_name, unit_price, quantity, subtotal)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (number, item["item_id"], item["name"], item["price"],
                          item["quantity"], item["subtotal"]))
        except (sqlite3.Error, ValueError) as exc:
            messagebox.showerror("Unable to place order", str(exc))
            self.load_gui_items()
            return

        if payment == "Online":
            self.show_online_payment_window(number, online, total)
        else:
            self.build_customer()
            messagebox.showinfo("Order placed", f"ORDER NUMBER: #{number}")

    def show_customer_receipt(self, order_number):
        """Display the customer receipt and a unique 1–50 order-ready code."""
        with connect_db() as conn:
            order = conn.execute("""
                SELECT customer_name, order_date, order_type, total,
                       payment_method, online_method, prep_time,
                       payment_status, confirmation_number, table_number
                FROM orders WHERE order_number=?
            """, (order_number,)).fetchone()
            items = conn.execute("""
                SELECT item_name, quantity, unit_price, subtotal
                FROM order_items WHERE order_number=? ORDER BY item_name
            """, (order_number,)).fetchall()
        if not order:
            return
        customer, date, order_type, total, payment, online, prep, pay_status, code_number, table_number = order

        receipt = tk.Toplevel(self.root)
        receipt.title(f"Receipt - Order #{order_number}")
        receipt.geometry("470x600")
        receipt.minsize(420, 500)
        receipt.configure(bg="white")
        receipt.transient(self.root)
        tk.Label(receipt, text="JOLLIBEE", bg="white", fg=self.RED,
                 font=("Arial", 22, "bold")).pack(pady=(16, 2))
        tk.Label(receipt, text="CUSTOMER ORDER RECEIPT", bg="white",
                 font=("Arial", 11, "bold")).pack(pady=(0, 10))
        content = tk.Frame(receipt, bg="white", padx=20)
        content.pack(fill="both", expand=True)
        lines = [
            f"Customer: {customer}", f"Order Number: {order_number}",
            f"Date: {date}", f"Order Type: {order_type}",
            "-" * 42,
            f"{'ITEM':22} {'QTY':>4} {'TOTAL':>10}", "-" * 42
        ]
        for name, qty, unit_price, subtotal in items:
            lines.append(f"{name[:22]:22} {qty:>4} {subtotal:>10.2f}")
        lines += [
            "-" * 42, f"TOTAL: PHP {total:,.2f}",
            f"Payment: {payment}" + (f" ({online})" if payment == "Online" else ""),
            f"Payment status: {pay_status}", f"Estimated preparation: {prep} minutes",
            "", f"CONFIRMATION NUMBER: {code_number}",
            "Keep this number and show it when claiming",
            "your order. Use it with your order number",
            "in CHECK ORDER STATUS on the home screen.",
            "", "Thank you for ordering! Enjoy your meal!"
        ]
        receipt_text = tk.Text(content, height=23, wrap="none",
                               font=("Consolas", 9), relief="flat", bg="white")
        receipt_text.pack(fill="both", expand=True)
        receipt_text.insert("1.0", "\n".join(lines))
        receipt_text.config(state="disabled")
        self.styled_button(receipt, "CLOSE RECEIPT", receipt.destroy,
                           color=self.RED, width=20).pack(pady=10)

    def check_customer_order(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Check Order Status")
        dialog.configure(bg=self.CREAM)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        tk.Label(dialog, text="CHECK YOUR ORDER", bg=self.CREAM, fg=self.RED,
                 font=("Arial", 16, "bold")).pack(padx=24, pady=(18, 10))
        tk.Label(dialog, text="Order number:", bg=self.CREAM).pack(anchor="w", padx=25)
        order_entry = tk.Entry(dialog, width=28, font=("Arial", 11))
        order_entry.pack(padx=25, pady=(3, 10))
        tk.Label(dialog, text="Confirmation number (1–50):",
                 bg=self.CREAM).pack(anchor="w", padx=25)
        code_entry = tk.Entry(dialog, width=28, font=("Arial", 11))
        code_entry.pack(padx=25, pady=(3, 12))

        def lookup():
            try:
                order_no = int(order_entry.get().strip())
                code_no = int(code_entry.get().strip())
                if not 1 <= code_no <= 50:
                    raise ValueError
            except ValueError:
                messagebox.showwarning(
                    "Invalid details",
                    "Enter a valid order number and a confirmation number from 1 to 50.",
                    parent=dialog
                )
                return
            with connect_db() as conn:
                row = conn.execute("""
                    SELECT customer_name, status, payment_status, confirmation_number
                    FROM orders WHERE order_number=?
                """, (order_no,)).fetchone()
            if not row or row[3] != code_no:
                messagebox.showerror(
                    "Order not found",
                    "The order number and confirmation number do not match.",
                    parent=dialog
                )
                return
            messagebox.showinfo(
                "Order status",
                f"Hello, {row[0]}!\n\nOrder #{order_no}\n"
                f"Payment: {row[2]}\nOrder status: {row[1]}",
                parent=dialog
            )
        self.styled_button(dialog, "CHECK STATUS", lookup,
                           color="#176B87", width=20).pack(pady=(0, 18))
        order_entry.focus_set()

    def show_online_payment_window(self, order_number, provider, total):
        """Show payment instructions and collect the customer's transaction reference."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Online Payment")
        dialog.configure(bg=self.CREAM)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="COMPLETE YOUR PAYMENT", bg=self.CREAM,
                 fg=self.RED, font=("Arial", 16, "bold")).pack(padx=25, pady=(18, 8))
        tk.Label(dialog, text=f"ORDER #{order_number}   |   PHP {total:,.2f}",
                 bg=self.CREAM, font=("Arial", 12, "bold")).pack(pady=5)
        tk.Label(dialog, text=f"Payment provider: {provider}", bg=self.CREAM,
                 font=("Arial", 11)).pack(pady=3)

        # Demo placeholders: replace these with the store's authorized payment details.
        tk.Label(dialog, text="STORE PAYMENT DETAILS", bg=self.CREAM,
                 font=("Arial", 10, "bold")).pack(pady=(12, 4))
        tk.Label(dialog, text=f"{provider} account name: Jollibee Store (DEMO)\n"
                              "Account number: 09XX XXX XXXX (PLACEHOLDER)",
                 bg="white", justify="center", padx=15, pady=12,
                 font=("Arial", 10)).pack(fill="x", padx=20)
        tk.Label(dialog,
                 text="Send the exact amount using your own payment app.\n"
                      "After paying, enter the transaction reference number below.\n"
                      "The admin will verify the payment using the store account.",
                 bg=self.CREAM, justify="center", wraplength=420).pack(padx=20, pady=12)

        reference = tk.StringVar()
        tk.Label(dialog, text="Transaction reference number:", bg=self.CREAM,
                 font=("Arial", 10, "bold")).pack(anchor="w", padx=25)
        entry = tk.Entry(dialog, textvariable=reference, width=38)
        entry.pack(padx=25, pady=6)
        entry.focus_set()

        def submit_reference():
            ref = reference.get().strip()
            if not ref:
                messagebox.showwarning("Reference required",
                                       "Please enter the transaction reference number.",
                                       parent=dialog)
                return
            with connect_db() as conn:
                cur = conn.execute("""
                    UPDATE orders SET payment_reference=?
                    WHERE order_number=? AND payment_status='Pending'
                """, (ref, order_number))
            if cur.rowcount != 1:
                messagebox.showerror("Unable to submit",
                                     "This order could not be updated.", parent=dialog)
                return
            dialog.destroy()
            self.build_customer()
            messagebox.showinfo("Order placed", f"ORDER NUMBER: #{order_number}")

        buttons = tk.Frame(dialog, bg=self.CREAM)
        buttons.pack(fill="x", padx=25, pady=(5, 18))
        self.styled_button(buttons, "SUBMIT REFERENCE", submit_reference,
                           color="#25833B", width=20).pack(side="left")

        # Keep the payment window open until the customer submits a reference.
        def require_reference_before_close():
            messagebox.showwarning(
                "Reference required",
                "Please enter your transaction reference number and click SUBMIT REFERENCE.",
                parent=dialog
            )

        dialog.protocol("WM_DELETE_WINDOW", require_reference_before_close)

    def admin_login(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Admin Login")
        dialog.configure(bg=self.CREAM)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        tk.Label(dialog, text="ADMIN LOGIN", bg=self.CREAM,
                 font=("Arial", 16, "bold")).pack(padx=25, pady=(20, 10))
        password = tk.Entry(dialog, show="*", width=25)
        password.pack(padx=25, pady=8)
        password.focus_set()

        def verify():
            if password.get() == ADMIN_PASSWORD:
                dialog.destroy()
                self.build_admin()
            else:
                messagebox.showerror("Access denied", "Incorrect admin password.")
        self.styled_button(dialog, "LOGIN", verify, width=18).pack(pady=15)
        password.bind("<Return>", lambda event: verify())

    def build_admin(self):
        self.clear()
        # Fit the complete admin layout inside the usable screen area.
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(1580, max(1100, screen_w - 40))
        win_h = min(900, max(650, screen_h - 110))
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.minsize(1000, 620)
        self.header("ADMIN PANEL", "Manage customer orders")

        style = ttk.Style(self.root)
        style.configure("Admin.Treeview", font=("Arial", 12), rowheight=34)
        style.configure("Admin.Treeview.Heading", font=("Arial", 12, "bold"))

        body = tk.Frame(self.root, bg=self.CREAM, padx=18, pady=8)
        body.pack(fill="both", expand=True)
        # Grid gives the footer and tools their own reserved rows. Only the order
        # table shrinks/grows, so REFRESH ORDERS can never be pushed off-screen.
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        back_row = tk.Frame(body, bg=self.CREAM)
        back_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        tk.Button(back_row, text="← BACK TO HOME", command=self.build_home,
                  bg="#666666", fg="white", activebackground=self.YELLOW,
                  activeforeground=self.DARK, font=("Arial", 10, "bold"),
                  relief="flat", padx=14, pady=5, cursor="hand2").pack(side="right")

        search_row = tk.Frame(body, bg=self.CREAM)
        search_row.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        tk.Label(search_row, text="SEARCH ORDER NUMBER", bg=self.CREAM, fg=self.RED,
                 font=("Arial", 11, "bold")).pack(side="left", padx=(2, 8))
        self.order_search_var = tk.StringVar()
        self.order_search_entry = tk.Entry(
            search_row, textvariable=self.order_search_var, font=("Arial", 12),
            width=22, relief="solid", bd=1
        )
        self.order_search_entry.pack(side="left", ipady=5)
        self.order_search_entry.bind("<KeyRelease>", lambda event: self.refresh_admin())
        self.styled_button(search_row, "CLEAR", self.clear_order_search,
                           color="#666666", width=9).pack(side="left", padx=7)
        tk.Label(search_row, text="Type an order number to filter the list",
                 bg=self.CREAM, fg="#666666", font=("Arial", 9)).pack(side="left", padx=5)

        self.checked_order_numbers = set()
        cols = ("number", "customer", "date", "type", "total", "payment", "paystatus", "prep", "status")
        table_frame = tk.Frame(body, bg=self.CREAM)
        table_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 6))
        self.orders_tree = ttk.Treeview(
            table_frame, columns=cols, show="tree headings", selectmode="browse",
            style="Admin.Treeview"
        )
        self.orders_tree.heading("#0", text="Select")
        self.orders_tree.column("#0", width=65, minwidth=55, stretch=False, anchor="center")
        headings = ["Order No.", "Customer", "Date", "Type", "Total",
                    "Payment", "Pay Status", "Prep", "Order Status"]
        widths = [90, 155, 165, 95, 115, 105, 125, 75, 135]
        for col, heading, width in zip(cols, headings, widths):
            self.orders_tree.heading(col, text=heading)
            self.orders_tree.column(col, width=width, minwidth=65, anchor="center", stretch=True)

        vertical_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.orders_tree.yview)
        horizontal_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.orders_tree.xview)
        self.orders_tree.configure(yscrollcommand=vertical_scroll.set,
                                   xscrollcommand=horizontal_scroll.set)
        self.orders_tree.grid(row=0, column=0, sticky="nsew")
        vertical_scroll.grid(row=0, column=1, sticky="ns")
        horizontal_scroll.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        self.orders_tree.bind("<Button-1>", self.toggle_order_checkbox, add="+")
        self.orders_tree.bind("<Double-1>", self.show_order_details)

        actions = tk.LabelFrame(body, text="ADMIN TOOLS", bg=self.CREAM, fg=self.RED,
                                font=("Arial", 12, "bold"), padx=9, pady=5)
        actions.grid(row=3, column=0, sticky="ew", pady=(0, 4))
        action_rows = [
            [("VERIFY PAYMENTS", self.verify_selected_payments, "#176B87"),
             ("REJECT PAYMENT", self.reject_selected_payments, "#A51D25"),
             ("UPDATE STATUS", self.update_gui_status, "#25833B")],
            [("DASHBOARD", self.show_dashboard, self.DARK),
             ("MOST BOUGHT ITEMS", self.show_most_bought_chart, "#8A4F9E"),
             ("INVENTORY", self.build_inventory, "#B66A00")],
            [("SAVE DAILY SALES", self.save_daily_sales, "#25833B"),
             ("SALES CHART", self.show_sales_chart, "#176B87"),
             ("DELETE SELECTED", self.delete_selected_orders, "#A51D25")],
        ]
        for col in range(3):
            actions.grid_columnconfigure(col, weight=1, uniform="admin_actions")
        for row_index, row_items in enumerate(action_rows):
            for col_index, (label, command, color) in enumerate(row_items):
                button = self.styled_button(actions, label, command, color=color, width=18)
                button.configure(font=("Arial", 10, "bold"), padx=8, pady=7)
                button.grid(row=row_index, column=col_index, sticky="ew", padx=5, pady=3)

        refresh_row = tk.Frame(body, bg=self.CREAM)
        refresh_row.grid(row=4, column=0, sticky="ew", pady=(0, 1))
        refresh_button = self.styled_button(
            refresh_row, "REFRESH ORDERS", self.refresh_admin,
            color=self.RED, width=24
        )
        refresh_button.configure(font=("Arial", 11, "bold"), padx=14, pady=7)
        refresh_button.pack(anchor="center")

        self.refresh_admin()
        self.schedule_screen_refresh("admin")

    def toggle_order_checkbox(self, event):
        """Toggle a row checkbox when its checkbox cell is clicked."""
        if self.orders_tree.identify_region(event.x, event.y) != "tree":
            return
        iid = self.orders_tree.identify_row(event.y)
        if not iid:
            return
        try:
            number = int(self.orders_tree.item(iid, "values")[0])
        except (ValueError, IndexError, TypeError):
            return
        if number in self.checked_order_numbers:
            self.checked_order_numbers.remove(number)
        else:
            self.checked_order_numbers.add(number)
        self.orders_tree.item(iid, text="☑" if number in self.checked_order_numbers else "☐")
        return "break"

    def clear_order_search(self):
        if hasattr(self, "order_search_var"):
            self.order_search_var.set("")
        self.refresh_admin()

    def refresh_admin(self):
        if not hasattr(self, "orders_tree") or not self.orders_tree.winfo_exists():
            return
        if not hasattr(self, "checked_order_numbers"):
            self.checked_order_numbers = set()
        for row in self.orders_tree.get_children():
            self.orders_tree.delete(row)
        with connect_db() as conn:
            rows = conn.execute("""
                SELECT order_number, customer_name, order_date, order_type,
                       total, payment_method, payment_status, prep_time, status
                FROM orders ORDER BY order_date DESC
            """).fetchall()
        search_text = (self.order_search_var.get().strip()
                       if hasattr(self, "order_search_var") else "")
        for row in rows:
            if search_text and search_text not in str(row[0]):
                continue
            iid = self.orders_tree.insert("", "end", text=(
                "☑" if row[0] in self.checked_order_numbers else "☐"), values=(
                row[0], row[1], row[2], row[3], f"PHP {row[4]:.2f}",
                row[5], row[6], f"{row[7]} min", row[8]))
        # Drop checks for orders that no longer exist in the database.
        existing = {int(self.orders_tree.item(iid, "values")[0])
                    for iid in self.orders_tree.get_children()}
        self.checked_order_numbers.intersection_update(existing)

    def show_admin_receipt(self, order_number):
        """Show the store/admin receipt only after payment has been accepted."""
        with connect_db() as conn:
            order = conn.execute("""
                SELECT customer_name, order_date, order_type, total,
                       payment_method, online_method, prep_time,
                       payment_status, status, confirmation_number, table_number
                FROM orders WHERE order_number=?
            """, (order_number,)).fetchone()
            items = conn.execute("""
                SELECT item_name, quantity, unit_price, subtotal
                FROM order_items WHERE order_number=? ORDER BY item_name
            """, (order_number,)).fetchall()
        if not order or order[7] != "Confirmed":
            return
        customer, date, order_type, total, payment, online, prep, pay_status, status, code, table_number = order
        receipt = tk.Toplevel(self.root)
        receipt.title(f"Admin Receipt - Order #{order_number}")
        receipt.geometry("500x610")
        receipt.minsize(440, 520)
        receipt.configure(bg="white")
        receipt.transient(self.root)
        tk.Label(receipt, text="JOLLIBEE", bg="white", fg=self.RED,
                 font=("Arial", 22, "bold")).pack(pady=(16, 2))
        tk.Label(receipt, text="OFFICIAL PAYMENT RECEIPT", bg="white",
                 font=("Arial", 11, "bold")).pack(pady=(0, 10))
        lines = [
            f"Order Number: {order_number}", f"Customer: {customer}",
            f"Date: {date}", f"Order Type: {order_type}",
            "-" * 44,
            f"{'ITEM':24} {'QTY':>4} {'SUBTOTAL':>12}", "-" * 44
        ]
        for name, qty, unit_price, subtotal in items:
            lines.append(f"{name[:24]:24} {qty:>4} {subtotal:>12.2f}")
        lines += [
            "-" * 44, f"TOTAL PAID: PHP {total:,.2f}",
            f"Payment Method: {payment}" + (f" ({online})" if payment == "Online" else ""),
            f"Payment Status: {pay_status}", f"Order Status: {status}",
            f"Preparation Time: {prep} minutes",
            f"Customer Confirmation No.: {code}",
            "", "PAYMENT ACCEPTED BY ADMIN", "Keep this receipt for store records."
        ]
        area = tk.Frame(receipt, bg="white", padx=20)
        area.pack(fill="both", expand=True)
        output = tk.Text(area, wrap="none", font=("Consolas", 9),
                         relief="flat", bg="white")
        output.pack(fill="both", expand=True)
        output.insert("1.0", "\n".join(lines))
        output.config(state="disabled")
        self.styled_button(receipt, "CLOSE RECEIPT", receipt.destroy,
                           color=self.RED, width=20).pack(pady=10)

    def verify_selected_payments(self):
        numbers = sorted(self.checked_order_numbers)
        if not numbers:
            messagebox.showwarning("Select orders", "Check one or more orders first.")
            return

        with connect_db() as conn:
            placeholders = ",".join("?" for _ in numbers)
            orders = conn.execute(
                f"SELECT order_number, customer_name, total, payment_method, "
                f"online_method, payment_status, payment_reference "
                f"FROM orders WHERE order_number IN ({placeholders}) ORDER BY order_number",
                numbers
            ).fetchall()
            order_items = {}
            for order in orders:
                order_items[order[0]] = conn.execute("""
                    SELECT item_name, quantity, unit_price, subtotal
                    FROM order_items WHERE order_number=? ORDER BY item_name
                """, (order[0],)).fetchall()

        if not orders:
            messagebox.showwarning("No orders", "No selected orders were found.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Review Order and Confirm Payment")
        dialog.geometry("680x590")
        dialog.minsize(560, 420)
        dialog.configure(bg=self.CREAM)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="PAYMENT VERIFICATION", bg=self.CREAM, fg=self.RED,
                 font=("Arial", 17, "bold")).pack(pady=(14, 4))
        tk.Label(dialog,
                 text="Review the ordered items and check the store's actual payment records.",
                 bg=self.CREAM, fg=self.DARK, wraplength=620).pack(pady=(0, 10))

        text_frame = tk.Frame(dialog, bg=self.CREAM)
        text_frame.pack(fill="both", expand=True, padx=16, pady=4)
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        details = tk.Text(text_frame, wrap="word", font=("Consolas", 10),
                          yscrollcommand=scrollbar.set, height=20)
        details.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=details.yview)

        for order in orders:
            number, customer, total, method, provider, pay_status, reference = order
            details.insert("end", f"ORDER #{number}  |  {customer}\n")
            details.insert("end", f"Payment: {method} {('(' + provider + ')') if method == 'Online' else ''}\n")
            details.insert("end", f"Payment status: {pay_status}\n")
            details.insert("end", f"Reference: {reference or 'Not submitted'}\n")
            details.insert("end", "-" * 58 + "\n")
            details.insert("end", f"{'ITEM':28} {'QTY':>4} {'PRICE':>9} {'SUBTOTAL':>11}\n")
            details.insert("end", "-" * 58 + "\n")
            for name, quantity, unit_price, subtotal in order_items.get(number, []):
                details.insert("end", f"{name[:28]:28} {quantity:>4} {unit_price:>9.2f} {subtotal:>11.2f}\n")
            details.insert("end", "-" * 58 + "\n")
            details.insert("end", f"ORDER TOTAL: PHP {total:,.2f}\n\n")
        details.config(state="disabled")

        button_row = tk.Frame(dialog, bg=self.CREAM)
        button_row.pack(fill="x", padx=16, pady=14)

        def confirm():
            confirmed = 0
            skipped = []
            with connect_db() as conn:
                for row in orders:
                    number, customer, total, method, provider, pay_status, reference = row
                    if pay_status != "Pending":
                        skipped.append(str(number))
                        continue
                    if method == "Online" and not reference:
                        skipped.append(str(number))
                        continue
                    cur = conn.execute("""
                        UPDATE orders
                        SET payment_status='Confirmed', status='Preparing'
                        WHERE order_number=? AND payment_status='Pending'
                    """, (number,))
                    confirmed += cur.rowcount
            dialog.destroy()
            self.refresh_admin()
            self.load_gui_items_if_customer_open()
            for order in orders:
                number = order[0]
                if str(number) not in skipped:
                    self.show_admin_receipt(number)
            message = f"Confirmed payment for {confirmed} order(s)."
            if skipped:
                message += "\nSkipped (already processed or missing online reference): " + ", ".join(skipped)
            messagebox.showinfo("Payment verification", message)

        self.styled_button(button_row, "CONFIRM PAYMENT", confirm,
                           color="#25833B", width=20).pack(side="left")
        self.styled_button(button_row, "CANCEL", dialog.destroy,
                           color="#666666", width=14).pack(side="right")

    def reject_selected_payments(self):
        numbers = sorted(self.checked_order_numbers)
        if not numbers:
            messagebox.showwarning("Select orders", "Check one or more orders first.")
            return

        # Only payments that are still Pending may be rejected. A verified
        # (Confirmed) payment is final and must never be changed to Rejected.
        with connect_db() as conn:
            placeholders = ",".join("?" for _ in numbers)
            rows = conn.execute(
                f"SELECT order_number, payment_status FROM orders "
                f"WHERE order_number IN ({placeholders})", numbers
            ).fetchall()
        pending_numbers = [number for number, status in rows if status == "Pending"]
        protected_numbers = [number for number, status in rows if status == "Confirmed"]

        if not pending_numbers:
            messagebox.showinfo(
                "Cannot reject payment",
                "None of the selected orders has a pending payment. "
                "Verified payments cannot be rejected."
            )
            return

        prompt = (
            f"Reject payment for {len(pending_numbers)} pending order(s)?\n"
            "Their reserved stock will be returned and the orders cancelled."
        )
        if protected_numbers:
            prompt += (
                "\n\nVerified orders will be skipped and cannot be rejected: "
                + ", ".join(str(number) for number in protected_numbers)
            )
        if not messagebox.askyesno("Reject payment", prompt):
            return

        rejected = 0
        with connect_db() as conn:
            for number in pending_numbers:
                # Conditional update protects against a payment being verified
                # between the selection check and this update.
                cur = conn.execute("""
                    UPDATE orders SET payment_status='Rejected', status='Cancelled'
                    WHERE order_number=? AND payment_status='Pending'
                """, (number,))
                if cur.rowcount != 1:
                    continue
                items = conn.execute(
                    "SELECT item_id, quantity FROM order_items WHERE order_number=?",
                    (number,)
                ).fetchall()
                for item_id, quantity in items:
                    conn.execute(
                        "UPDATE menu_items SET stock=stock+? WHERE item_id=?",
                        (quantity, item_id)
                    )
                rejected += 1

        self.refresh_admin()
        self.load_gui_items_if_customer_open()
        message = f"Rejected {rejected} pending payment(s)."
        if protected_numbers:
            message += "\nVerified payments were left unchanged."
        messagebox.showinfo("Payment rejection result", message)

    def load_gui_items_if_customer_open(self):
        # Refresh inventory display if the customer screen happens to be open.
        if hasattr(self, "menu_tree") and self.menu_tree.winfo_exists():
            self.load_gui_items()

    def selected_order_number(self, event=None):
        iid = self.orders_tree.identify_row(event.y) if event is not None else None
        if not iid:
            selected = self.orders_tree.selection()
            iid = selected[0] if selected else None
        if not iid:
            messagebox.showwarning("Select order", "Please select an order first.")
            return None
        return int(self.orders_tree.item(iid, "values")[0])

    def show_order_details(self, event=None):
        number = self.selected_order_number(event)
        if number is None:
            return
        with connect_db() as conn:
            order = conn.execute("SELECT * FROM orders WHERE order_number=?",
                                 (number,)).fetchone()
            items = conn.execute("""
                SELECT item_name, unit_price, quantity, subtotal
                FROM order_items WHERE order_number=?
            """, (number,)).fetchall()
        if not order:
            return
        details = [
            f"Order Number: {order[0]}",
            f"Customer: {order[1]}",
            f"Date: {order[2]}",
            f"Order Type: {order[3]}",
            "", "ORDERED ITEMS", "-" * 38
        ]
        for name, price, qty, subtotal in items:
            details.append(f"{name} x{qty} @ PHP {price:.2f} = PHP {subtotal:.2f}")
        details += ["-" * 38, f"TOTAL: PHP {order[4]:.2f}",
                    f"Payment: {order[5]} ({order[6]})",
                    f"Payment Status: {order[9] if len(order) > 9 else 'Confirmed'}",
                    f"Payment Reference: {order[10] if len(order) > 10 else ''}",
                    f"Confirmation Number: {order[11] if len(order) > 11 else 'N/A'}",
                    f"Preparation: {order[7]} minutes",
                    f"Order Status: {order[8]}"]
        messagebox.showinfo("Order Details", "\n".join(details))

    def update_gui_status(self):
        numbers = sorted(self.checked_order_numbers)
        if not numbers:
            messagebox.showwarning("Select orders", "Please check one or more orders first.")
            return
        with connect_db() as conn:
            placeholders = ",".join("?" for _ in numbers)
            unconfirmed = conn.execute(
                f"SELECT order_number FROM orders WHERE order_number IN ({placeholders}) "
                "AND payment_status!='Confirmed'", numbers
            ).fetchall()
        if unconfirmed:
            blocked = ", ".join(str(row[0]) for row in unconfirmed)
            messagebox.showwarning(
                "Payment not confirmed",
                f"These orders cannot be processed yet: {blocked}.\n"
                "Confirm their payment first."
            )
            return
        label = f"{len(numbers)} selected order(s)" if len(numbers) > 1 else f"Order #{numbers[0]}"
        dialog = tk.Toplevel(self.root)
        dialog.title("Update Order Status")
        dialog.configure(bg=self.CREAM)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        tk.Label(dialog, text=f"Update status for {label}", bg=self.CREAM,
                 font=("Arial", 11, "bold")).pack(padx=20, pady=15)
        status = tk.StringVar(value="Preparing")
        ttk.Combobox(dialog, textvariable=status,
                     values=["Preparing", "Ready", "Completed"],
                     state="readonly", width=22).pack(padx=20, pady=8)

        def save():
            target_status = status.get()
            with connect_db() as conn:
                current_rows = conn.execute(
                    f"SELECT order_number, status FROM orders WHERE order_number IN ({placeholders})",
                    numbers
                ).fetchall()
                stage = {"Preparing": 1, "Ready": 2, "Completed": 3}
                invalid = [
                    str(order_no) for order_no, current in current_rows
                    if current not in stage
                    or target_status not in stage
                    or stage[target_status] < stage[current]
                    or (target_status == "Completed" and current != "Ready")
                ]
                if invalid:
                    messagebox.showwarning(
                        "Invalid status transition",
                        "Orders must follow Preparing → Ready → Completed. "
                        "These orders cannot move to the selected status: " + ", ".join(invalid),
                        parent=dialog
                    )
                    return
                conn.executemany("UPDATE orders SET status=? WHERE order_number=?",
                                 [(target_status, number) for number in numbers])
            dialog.destroy()
            self.refresh_admin()
            messagebox.showinfo("Updated", f"Status updated for {len(numbers)} order(s).")
        self.styled_button(dialog, "SAVE STATUS", save, width=18).pack(pady=15)

    def delete_selected_orders(self):
        numbers = sorted(self.checked_order_numbers)
        if not numbers:
            messagebox.showwarning("Select orders", "Please check one or more orders to delete.")
            return
        if not messagebox.askyesno(
            "Confirm deletion",
            f"Permanently delete {len(numbers)} selected order(s)?\nTheir order items will also be deleted. This cannot be undone."
        ):
            return
        with connect_db() as conn:
            # Pending orders have reserved stock. Return that stock before deleting
            # them; confirmed orders have already been sold and must not be returned.
            for number in numbers:
                order = conn.execute(
                    "SELECT payment_status FROM orders WHERE order_number=?", (number,)
                ).fetchone()
                if order and order[0] == "Pending":
                    reserved_items = conn.execute(
                        "SELECT item_id, quantity FROM order_items WHERE order_number=?",
                        (number,)
                    ).fetchall()
                    for item_id, quantity in reserved_items:
                        conn.execute(
                            "UPDATE menu_items SET stock=stock+? WHERE item_id=?",
                            (quantity, item_id)
                        )
                conn.execute("DELETE FROM orders WHERE order_number=?", (number,))
        self.checked_order_numbers.difference_update(numbers)
        self.load_gui_items_if_customer_open()
        if hasattr(self, "inventory_tree") and self.inventory_tree.winfo_exists():
            self.refresh_inventory()
        self.refresh_admin()
        messagebox.showinfo("Orders deleted", f"{len(numbers)} order(s) deleted successfully.")

    def build_inventory(self):
        self.clear()
        self.header("INVENTORY MANAGEMENT", "Update stock and monitor sold-out items")
        body = tk.Frame(self.root, bg=self.CREAM, padx=18, pady=15)
        body.pack(fill="both", expand=True)

        top = tk.Frame(body, bg=self.CREAM)
        top.pack(fill="x", pady=(0, 12))
        self.styled_button(top, "REFRESH", self.refresh_inventory,
                           width=14).pack(side="left")
        self.styled_button(top, "UPDATE SELECTED STOCK", self.update_inventory_stock,
                           color="#25833B", width=21).pack(side="left", padx=8)
        self.styled_button(top, "ADD NEW MENU", self.add_menu_item,
                           color="#176B87", width=15).pack(side="left")
        self.styled_button(top, "DELETE SELECTED", self.delete_menu_item,
                           color="#A51D25", width=16).pack(side="left", padx=8)
        tk.Button(top, text="←", command=self.build_admin,
                  bg="#666666", fg="white", activebackground=self.YELLOW,
                  activeforeground=self.DARK, font=("Arial", 16, "bold"),
                  relief="flat", width=3, cursor="hand2").pack(side="right")

        # Keep checkbox state independently of Treeview row selection so multiple
        # inventory items can be checked without Ctrl/Shift and survive refreshes.
        if not hasattr(self, "checked_inventory_ids"):
            self.checked_inventory_ids = set()
        cols = ("id", "name", "category", "price", "stock", "status")
        self.inventory_tree = ttk.Treeview(
            body, columns=cols, show="tree headings", selectmode="browse"
        )
        self.inventory_tree.heading("#0", text="Select")
        self.inventory_tree.column("#0", width=55, minwidth=55,
                                   stretch=False, anchor="center")
        for col, label, width in [
            ("id", "ID", 55), ("name", "Food Item", 300),
            ("category", "Category", 190), ("price", "Price", 100),
            ("stock", "Stock Qty", 100), ("status", "Availability", 120)
        ]:
            self.inventory_tree.heading(col, text=label)
            self.inventory_tree.column(col, width=width, anchor="center")
        self.inventory_tree.pack(fill="both", expand=True)
        self.inventory_tree.bind("<Button-1>", self.toggle_inventory_checkbox, add="+")
        self.inventory_tree.tag_configure("soldout", foreground="#D71920")
        self.refresh_inventory()
        self.schedule_screen_refresh("inventory")

    def toggle_inventory_checkbox(self, event):
        """Toggle an inventory checkbox without using Ctrl or Shift."""
        if self.inventory_tree.identify_region(event.x, event.y) != "tree":
            return
        iid = self.inventory_tree.identify_row(event.y)
        if not iid:
            return
        try:
            item_id = int(self.inventory_tree.item(iid, "values")[0])
        except (ValueError, IndexError, TypeError):
            return
        if item_id in self.checked_inventory_ids:
            self.checked_inventory_ids.remove(item_id)
        else:
            self.checked_inventory_ids.add(item_id)
        self.inventory_tree.item(
            iid, text="☑" if item_id in self.checked_inventory_ids else "☐"
        )
        return "break"

    def refresh_inventory(self):
        if not hasattr(self, "inventory_tree") or not self.inventory_tree.winfo_exists():
            return
        if not hasattr(self, "checked_inventory_ids"):
            self.checked_inventory_ids = set()
        for row in self.inventory_tree.get_children():
            self.inventory_tree.delete(row)
        with connect_db() as conn:
            rows = conn.execute("""
                SELECT m.item_id, m.item_name, c.category_name, m.price, m.stock, m.is_available
                FROM menu_items m
                JOIN menu_categories c ON c.category_id=m.category_id
                ORDER BY c.category_name, m.item_name
            """).fetchall()
        for item_id, name, category, price, stock, is_available in rows:
            status = "REMOVED" if not is_available else ("SOLD OUT" if stock <= 0 else "AVAILABLE")
            self.inventory_tree.insert(
                "", "end",
                text="☑" if item_id in self.checked_inventory_ids else "☐",
                values=(item_id, name, category, f"PHP {price:.2f}", stock, status),
                tags=("soldout",) if status != "AVAILABLE" else ()
            )
        existing_ids = {
            int(self.inventory_tree.item(iid, "values")[0])
            for iid in self.inventory_tree.get_children()
        }
        self.checked_inventory_ids.intersection_update(existing_ids)

    def add_menu_item(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Menu Item")
        dialog.configure(bg=self.CREAM)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="ADD NEW MENU ITEM", bg=self.CREAM,
                 font=("Arial", 14, "bold")).pack(padx=24, pady=(18, 12))
        form = tk.Frame(dialog, bg=self.CREAM)
        form.pack(padx=24, pady=5)
        fields = {}
        for row, label in enumerate(("Menu name", "Category", "Price (PHP)", "Preparation time (minutes)", "Initial stock")):
            tk.Label(form, text=label + ":", bg=self.CREAM, anchor="w").grid(row=row, column=0, sticky="w", padx=(0, 12), pady=7)
            if label == "Category":
                widget = ttk.Combobox(form, values=[r[1] for r in get_categories()], width=27)
            else:
                widget = tk.Entry(form, width=30)
            widget.grid(row=row, column=1, pady=7)
            fields[label] = widget

        def save():
            name = fields["Menu name"].get().strip()
            category = fields["Category"].get().strip()
            try:
                price = float(fields["Price (PHP)"].get())
                prep = int(fields["Preparation time (minutes)"].get())
                stock = int(fields["Initial stock"].get())
                if not name or not category or price <= 0 or prep < 0 or stock < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid details", "Enter a name/category, a positive price, and whole numbers of 0 or higher for prep time and stock.", parent=dialog)
                return
            with connect_db() as conn:
                conn.execute("INSERT OR IGNORE INTO menu_categories(category_name) VALUES (?)", (category,))
                category_id = conn.execute("SELECT category_id FROM menu_categories WHERE category_name=?", (category,)).fetchone()[0]
                duplicate = conn.execute("SELECT 1 FROM menu_items WHERE lower(item_name)=lower(?) AND is_available=1", (name,)).fetchone()
                if duplicate:
                    messagebox.showerror("Duplicate menu", "An active menu item with this name already exists.", parent=dialog)
                    return
                item_id = conn.execute("SELECT COALESCE(MAX(item_id), 0) + 1 FROM menu_items").fetchone()[0]
                conn.execute("INSERT INTO menu_items(item_id, category_id, item_name, price, prep_time, is_available, stock) VALUES (?, ?, ?, ?, ?, 1, ?)",
                             (item_id, category_id, name, price, prep, stock))
            dialog.destroy()
            self.refresh_inventory()
            messagebox.showinfo("Menu added", f"{name} was added to the menu.")

        self.styled_button(dialog, "SAVE MENU ITEM", save, width=20).pack(pady=16)

    def delete_menu_item(self):
        item_ids = sorted(getattr(self, "checked_inventory_ids", set()))
        if not item_ids:
            messagebox.showwarning(
                "Select menu", "Please check one or more menu items to delete."
            )
            return

        with connect_db() as conn:
            placeholders = ",".join("?" for _ in item_ids)
            selected_rows = conn.execute(
                f"SELECT item_id, item_name, is_available FROM menu_items "
                f"WHERE item_id IN ({placeholders})", item_ids
            ).fetchall()

        active_rows = [row for row in selected_rows if row[2]]
        if not active_rows:
            messagebox.showinfo(
                "Already removed", "All checked menu items are already removed."
            )
            return
        names = [row[1] for row in active_rows]
        preview = "\n".join(f"• {name}" for name in names[:8])
        if len(names) > 8:
            preview += f"\n...and {len(names) - 8} more"
        if not messagebox.askyesno(
            "Confirm menu deletion",
            f"Remove {len(names)} selected item(s) from the customer menu?\n\n"
            f"{preview}\n\nPast order records will be preserved."
        ):
            return

        with connect_db() as conn:
            for item_id, item_name, is_available in active_rows:
                used = conn.execute(
                    "SELECT COUNT(*) FROM order_items WHERE item_id=?", (item_id,)
                ).fetchone()[0]
                if used:
                    # Preserve menu rows referenced by historical order records.
                    conn.execute(
                        "UPDATE menu_items SET is_available=0 WHERE item_id=?",
                        (item_id,)
                    )
                else:
                    conn.execute("DELETE FROM menu_items WHERE item_id=?", (item_id,))

        self.checked_inventory_ids.difference_update(item_ids)
        self.refresh_inventory()
        messagebox.showinfo(
            "Menu deleted", f"{len(active_rows)} selected item(s) removed from the customer menu."
        )

    def update_inventory_stock(self):
        item_ids = sorted(getattr(self, "checked_inventory_ids", set()))
        if not item_ids:
            messagebox.showwarning(
                "Select items", "Please check one or more inventory items first."
            )
            return

        with connect_db() as conn:
            placeholders = ",".join("?" for _ in item_ids)
            selected_rows = conn.execute(
                f"SELECT item_id, item_name, stock FROM menu_items "
                f"WHERE item_id IN ({placeholders}) ORDER BY item_name", item_ids
            ).fetchall()
        if not selected_rows:
            self.checked_inventory_ids.clear()
            self.refresh_inventory()
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Bulk Update Inventory")
        dialog.configure(bg=self.CREAM)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        tk.Label(
            dialog, text=f"Update stock for {len(selected_rows)} selected item(s)",
            bg=self.CREAM, font=("Arial", 12, "bold")
        ).pack(padx=22, pady=(18, 8))
        names = ", ".join(row[1] for row in selected_rows[:5])
        if len(selected_rows) > 5:
            names += f", and {len(selected_rows) - 5} more"
        tk.Label(dialog, text=names, bg=self.CREAM, wraplength=340,
                 justify="center").pack(padx=22, pady=4)
        tk.Label(
            dialog, text="New quantity for all selected items (0 = SOLD OUT):",
            bg=self.CREAM
        ).pack(padx=22, pady=(8, 0))
        quantity = tk.Entry(dialog, width=18, justify="center")
        quantity.insert(0, str(selected_rows[0][2]))
        quantity.pack(padx=22, pady=10)
        quantity.focus_set()

        def save():
            try:
                amount = int(quantity.get())
                if amount < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Invalid stock", "Enter a whole number (0 or higher).", parent=dialog
                )
                return
            with connect_db() as conn:
                conn.executemany(
                    "UPDATE menu_items SET stock=? WHERE item_id=?",
                    [(amount, item_id) for item_id, _name, _stock in selected_rows]
                )
            dialog.destroy()
            self.refresh_inventory()
            messagebox.showinfo(
                "Inventory updated",
                f"Stock updated to {amount} for {len(selected_rows)} item(s).",
                parent=self.root
            )

        self.styled_button(dialog, "SAVE STOCK", save, width=18).pack(pady=15)
        quantity.bind("<Return>", lambda event: save())

    def show_sales_chart(self):
        window = tk.Toplevel(self.root)
        window.title("Daily Sales Chart")
        window.geometry("850x560")
        window.configure(bg=self.CREAM)
        tk.Label(window, text="DAILY SALES CHART", bg=self.CREAM, fg=self.RED,
                 font=("Arial", 18, "bold")).pack(pady=(15, 5))
        tk.Label(window, text="Sales are grouped by order date",
                 bg=self.CREAM, fg=self.DARK).pack()

        with connect_db() as conn:
            rows = conn.execute("""
                SELECT substr(order_date, 1, 10) AS day,
                       COALESCE(SUM(total), 0)
                FROM orders
                WHERE payment_status='Confirmed'
                GROUP BY day
                ORDER BY day DESC
                LIMIT 7
            """).fetchall()
        rows.reverse()

        canvas = tk.Canvas(window, bg="white", height=390, highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=20, pady=18)
        canvas.update_idletasks()
        width = max(canvas.winfo_width(), 760)
        height = 390
        left, right, top, bottom = 75, width - 25, 25, 320
        canvas.create_line(left, top, left, bottom, fill="#555555", width=2)
        canvas.create_line(left, bottom, right, bottom, fill="#555555", width=2)

        if not rows or max((r[1] for r in rows), default=0) <= 0:
            canvas.create_text(width / 2, 170, text="No sales data available yet.",
                               font=("Arial", 14), fill=self.DARK)
            return

        max_sales = max(r[1] for r in rows)
        chart_height = bottom - top
        for tick in range(5):
            value = max_sales * tick / 4
            y = bottom - chart_height * tick / 4
            canvas.create_line(left, y, right, y, fill="#E5E5E5")
            canvas.create_text(left - 8, y, text=f"{value:,.0f}",
                               anchor="e", font=("Arial", 8))
        slot = (right - left) / max(len(rows), 1)
        bar_width = min(55, slot * 0.58)
        for i, (day, sales) in enumerate(rows):
            x = left + slot * (i + 0.5)
            bar_height = (sales / max_sales) * chart_height if max_sales else 0
            canvas.create_rectangle(x - bar_width / 2, bottom - bar_height,
                                    x + bar_width / 2, bottom,
                                    fill=self.RED, outline="")
            canvas.create_text(x, bottom - bar_height - 12,
                               text=f"₱{sales:,.0f}", font=("Arial", 8, "bold"))
            canvas.create_text(x, bottom + 18, text=day[5:],
                               font=("Arial", 9))
        total = sum(r[1] for r in rows)
        tk.Label(window, text=f"Total sales shown: PHP {total:,.2f}",
                 bg=self.CREAM, fg=self.RED,
                 font=("Arial", 13, "bold")).pack(pady=(0, 12))

    def show_most_bought_chart(self):
        """Display the ten menu items with the highest total quantity sold."""
        window = tk.Toplevel(self.root)
        window.title("Most Bought Items")
        window.geometry("900x620")
        window.configure(bg=self.CREAM)

        tk.Label(window, text="MOST BOUGHT ITEMS", bg=self.CREAM, fg=self.RED,
                 font=("Arial", 18, "bold")).pack(pady=(15, 5))
        tk.Label(window, text="Ranked by total quantity sold across all orders",
                 bg=self.CREAM, fg=self.DARK).pack()

        with connect_db() as conn:
            rows = conn.execute("""
                SELECT oi.item_name, SUM(oi.quantity) AS units_sold
                FROM order_items oi
                INNER JOIN orders o ON o.order_number = oi.order_number
                WHERE o.payment_status='Confirmed'
                GROUP BY oi.item_name
                ORDER BY units_sold DESC, oi.item_name ASC
                LIMIT 10
            """).fetchall()

        canvas = tk.Canvas(window, bg="white", height=470, highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=20, pady=18)
        canvas.update_idletasks()

        width = max(canvas.winfo_width(), 820)
        height = 470
        left, right, top, bottom = 245, width - 45, 30, height - 35
        canvas.create_line(left, top, left, bottom, fill="#555555", width=2)
        canvas.create_line(left, bottom, right, bottom, fill="#555555", width=2)

        if not rows:
            canvas.create_text(width / 2, height / 2,
                               text="No item sales data available yet.",
                               font=("Arial", 14), fill=self.DARK)
            return

        max_units = max(row[1] for row in rows)
        chart_width = right - left
        slot = (bottom - top) / len(rows)
        bar_height = min(25, slot * 0.62)

        for tick in range(5):
            value = max_units * tick / 4
            x = left + chart_width * tick / 4
            canvas.create_line(x, top, x, bottom, fill="#E5E5E5")
            canvas.create_text(x, bottom + 15, text=f"{value:.0f}",
                               font=("Arial", 8))

        for index, (item_name, units_sold) in enumerate(rows):
            y = top + slot * (index + 0.5)
            bar_width = (units_sold / max_units) * chart_width if max_units else 0
            canvas.create_text(left - 10, y, text=item_name,
                               anchor="e", font=("Arial", 9))
            canvas.create_rectangle(left, y - bar_height / 2,
                                    left + bar_width, y + bar_height / 2,
                                    fill=self.RED, outline="")
            canvas.create_text(min(left + bar_width + 25, right - 5), y,
                               text=str(units_sold), anchor="w",
                               font=("Arial", 9, "bold"), fill=self.DARK)

        tk.Label(window, text=f"Top item: {rows[0][0]} ({rows[0][1]} units sold)",
                 bg=self.CREAM, fg=self.RED,
                 font=("Arial", 13, "bold")).pack(pady=(0, 12))

    def save_daily_sales(self):
        """Export a date-specific, confirmed-sales report as an Excel-friendly CSV."""
        report_date = simpledialog.askstring(
            "Save Daily Sales",
            "Enter report date (YYYY-MM-DD):",
            initialvalue=datetime.now().strftime("%Y-%m-%d"),
            parent=self.root
        )
        if report_date is None:
            return
        try:
            datetime.strptime(report_date.strip(), "%Y-%m-%d")
        except ValueError:
            messagebox.showerror(
                "Invalid date", "Please use the YYYY-MM-DD date format.",
                parent=self.root
            )
            return
        report_date = report_date.strip()

        with connect_db() as conn:
            summary = conn.execute("""
                SELECT COUNT(*), COALESCE(SUM(total), 0)
                FROM orders
                WHERE substr(order_date, 1, 10)=? AND payment_status='Confirmed'
            """, (report_date,)).fetchone()
            rows = conn.execute("""
                SELECT o.order_number, o.customer_name, o.order_date,
                       o.order_type, oi.item_name, oi.quantity,
                       oi.unit_price, oi.subtotal, o.total,
                       o.payment_method, o.online_method, o.payment_status,
                       o.status
                FROM orders o
                JOIN order_items oi ON oi.order_number=o.order_number
                WHERE substr(o.order_date, 1, 10)=?
                  AND o.payment_status='Confirmed'
                ORDER BY o.order_date, o.order_number, oi.item_name
            """, (report_date,)).fetchall()

        filename = f"jollibee_daily_sales_{report_date}.csv"
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save Daily Sales Report",
            initialfile=filename,
            defaultextension=".csv",
            filetypes=[("CSV file (opens in Excel)", "*.csv"),
                       ("All files", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow(["JOLLIBEE - DAILY SALES REPORT"])
                writer.writerow(["Report Date", report_date])
                writer.writerow(["Confirmed Orders", summary[0]])
                writer.writerow(["TOTAL DAILY SALES (PHP)", f"{summary[1]:.2f}"])
                writer.writerow([])
                writer.writerow([
                    "Order Number", "Customer", "Order Date", "Order Type",
                    "Item", "Quantity", "Unit Price (PHP)",
                    "Item Subtotal (PHP)", "Order Total (PHP)",
                    "Payment Method", "Online Provider", "Payment Status",
                    "Order Status"
                ])
                writer.writerows(rows)
        except OSError as exc:
            messagebox.showerror("Save failed", f"Could not save the report:\n{exc}",
                                 parent=self.root)
            return

        messagebox.showinfo(
            "Daily Sales Saved",
            f"Daily sales report saved successfully.\n\n"
            f"Date: {report_date}\n"
            f"Confirmed orders: {summary[0]}\n"
            f"Total sales: PHP {summary[1]:,.2f}",
            parent=self.root
        )

    def show_dashboard(self):
        with connect_db() as conn:
            summary = conn.execute("""
                SELECT COUNT(*), COALESCE(SUM(CASE WHEN payment_status='Confirmed' THEN total ELSE 0 END),0),
                       SUM(CASE WHEN status!='Completed' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN payment_status='Pending' THEN 1 ELSE 0 END)
                FROM orders
            """).fetchone()
            statuses = conn.execute("""
                SELECT status, COUNT(*) FROM orders GROUP BY status
            """).fetchall()
        pending = summary[2] or 0
        completed = summary[3] or 0
        pending_payments = summary[4] or 0
        text = (f"TOTAL ORDERS: {summary[0]}\n"
                f"TOTAL SALES: PHP {summary[1]:,.2f}\n"
                f"PENDING ORDERS: {pending}\n"
                f"COMPLETED ORDERS: {completed}\n"
                f"PENDING PAYMENTS: {pending_payments}\n\n"
                "ORDER STATUS SUMMARY\n")
        text += "\n".join(f"{status}: {count}" for status, count in statuses)
        messagebox.showinfo("Admin Dashboard", text)


if __name__ == "__main__":
    initialize_database()
    root = tk.Tk()
    app = JollibeeGUI(root)
    root.mainloop()
