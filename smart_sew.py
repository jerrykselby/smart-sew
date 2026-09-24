import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import json
import os
import csv
from datetime import datetime

class TailorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart_Sew")
        self.root.geometry("1020x920")
        
        # Track editing state and current items list
        self.current_order_id = None
        self.current_order_items = []
        
        # Track current measurement editing state
        self.current_meas_id = None
        
        # Track current filter state
        self.current_status_filter = "All"
        
        # Connect to Database on Startup
        self.setup_database()

        # Create Notebook (Tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Tab 1: Orders
        self.tab_orders = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_orders, text="Orders")

        # Tab 2: Measurements
        self.tab_measurements = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_measurements, text="Measurements")

        self.setup_order_interface()
        self.setup_measurement_interface()
        
        self.refresh_treeview()

    def setup_database(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "smart_sew_database.db")
        
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
        # Measurements table without phone number
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY,
                client_name TEXT,
                gender TEXT,
                measurements_data TEXT
            )
        ''')
        
        # Orders table with phone number
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                client_name TEXT,
                phone_number TEXT,
                status TEXT,
                due_date TEXT,
                items_json TEXT,
                total_price TEXT,
                is_paid INTEGER DEFAULT 0
            )
        ''')
        
        # Migration check: remove phone number from measurements if present from previous version
        self.cursor.execute("PRAGMA table_info(measurements)")
        meas_cols = [c[1] for c in self.cursor.fetchall()]
        if 'phone_number' in meas_cols:
            self.cursor.execute("CREATE TABLE measurements_new (id INTEGER PRIMARY KEY, client_name TEXT, gender TEXT, measurements_data TEXT)")
            self.cursor.execute("SELECT id, client_name, gender, measurements_data FROM measurements")
            rows = self.cursor.fetchall()
            for row in rows:
                self.cursor.execute("INSERT INTO measurements_new (id, client_name, gender, measurements_data) VALUES (?, ?, ?, ?)",
                                    (row[0], row[1], row[2], row[3]))
            self.cursor.execute("DROP TABLE measurements")
            self.cursor.execute("ALTER TABLE measurements_new RENAME TO measurements")
            self.conn.commit()

        # Migration check for orders table
        self.cursor.execute("PRAGMA table_info(orders)")
        cols = [c[1] for c in self.cursor.fetchall()]
        if 'phone_number' not in cols:
            self.cursor.execute("ALTER TABLE orders ADD COLUMN phone_number TEXT")
        if 'items_json' not in cols:
            self.cursor.execute("ALTER TABLE orders ADD COLUMN items_json TEXT")
        if 'total_price' not in cols:
            self.cursor.execute("ALTER TABLE orders ADD COLUMN total_price TEXT")
        if 'is_paid' not in cols:
            self.cursor.execute("ALTER TABLE orders ADD COLUMN is_paid INTEGER DEFAULT 0")
            
        self.conn.commit()

    def center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")

    def setup_measurement_interface(self):
        # Create a Master Container and Center It 
        container = ttk.Frame(self.tab_measurements)
        container.pack(expand=True)

        # Top Section: Search for Clients 
        search_frame = ttk.LabelFrame(container, text="Search for Clients")
        search_frame.grid(row=0, column=0, columnspan=4, sticky='ew', padx=10, pady=10)
        
        ttk.Label(search_frame, text="Client Name:").pack(side='left', padx=5, pady=5)
        self.meas_search_entry = ttk.Entry(search_frame, width=20)
        self.meas_search_entry.pack(side='left', padx=5, pady=5)
        
        ttk.Button(search_frame, text="Search", command=self.search_measurements).pack(side='left', padx=3, pady=5)
        ttk.Button(search_frame, text="Clear Form", command=self.clear_measurement_form).pack(side='left', padx=3, pady=5)
        ttk.Button(search_frame, text="View All", command=self.view_all_clients).pack(side='left', padx=3, pady=5)

        # Header 
        ttk.Label(container, text="Client Measurements Form", font=("Helvetica", 14, "bold")).grid(row=1, column=0, columnspan=4, pady=15)
        
        # Basic Info 
        ttk.Label(container, text="Client Name:").grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.meas_name = ttk.Entry(container, width=25)
        self.meas_name.grid(row=2, column=1, sticky='w', padx=5, pady=5)

        ttk.Label(container, text="Gender:").grid(row=2, column=2, sticky='e', padx=5, pady=5)
        self.meas_gender = ttk.Combobox(container, values=["Male", "Female"], width=22, state="readonly")
        self.meas_gender.set("Select")
        self.meas_gender.grid(row=2, column=3, sticky='w', padx=5, pady=5)

        # Body Measurements 
        measurements_list = [
            "Neck", "Chest / Bust", "Under Bust", "Waist", "Hips", 
            "Shoulder to Shoulder", "Shoulder to Waist", "Armhole", 
            "Bicep", "Sleeve Length", "Wrist", "Torso Length", 
            "Thigh", "Knee", "Calf", "Ankle", "Inseam", "Outseam",
            "Total Height"
        ]

        self.meas_entries = {}
        row_idx = 3
        col_idx = 0

        for m in measurements_list:
            ttk.Label(container, text=f"{m}:").grid(row=row_idx, column=col_idx, sticky='e', padx=5, pady=5)
            entry = ttk.Entry(container, width=15)
            entry.grid(row=row_idx, column=col_idx+1, sticky='w', padx=5, pady=5)
            self.meas_entries[m] = entry
            
            col_idx += 2
            if col_idx > 2:
                col_idx = 0
                row_idx += 1

        # Action Buttons Frame (Save & Delete) 
        meas_btn_frame = ttk.Frame(container)
        meas_btn_frame.grid(row=row_idx+1, column=0, columnspan=4, pady=20)

        ttk.Button(meas_btn_frame, text="Save Measurements", command=self.save_measurements).pack(side='left', padx=5)
        ttk.Button(meas_btn_frame, text="Delete Client", command=self.delete_measurements).pack(side='left', padx=5)

    def setup_order_interface(self):
        # Master Container for the Orders Tab 
        orders_master_page = ttk.Frame(self.tab_orders)
        orders_master_page.pack(expand=True, fill='both', padx=15, pady=15)

        # 1. Frame for Order Inputs (Compact and centered, NOT stretched)
        input_container = ttk.Frame(orders_master_page)
        input_container.pack(pady=5)
        
        input_frame = ttk.LabelFrame(input_container, text="Order Management")
        input_frame.pack(padx=5, pady=5)
        
        input_frame.columnconfigure(1, weight=1)
        input_frame.columnconfigure(3, weight=1)

        # Order General Info (Row 0: Client Name & Phone Number)
        ttk.Label(input_frame, text="Client Name:").grid(row=0, column=0, sticky='e', padx=8, pady=8)
        self.order_client_name = ttk.Entry(input_frame, width=22)
        self.order_client_name.grid(row=0, column=1, padx=8, pady=8, sticky='ew')

        ttk.Label(input_frame, text="Phone Number:").grid(row=0, column=2, sticky='e', padx=8, pady=8)
        self.order_client_phone = ttk.Entry(input_frame, width=18)
        self.order_client_phone.grid(row=0, column=3, padx=8, pady=8, sticky='ew')

        # Row 1: Due Date & Status
        ttk.Label(input_frame, text="Due Date (YYYY-MM-DD):").grid(row=1, column=0, sticky='e', padx=8, pady=8)
        self.order_due_date = ttk.Entry(input_frame, width=22)
        self.order_due_date.grid(row=1, column=1, padx=8, pady=8, sticky='ew')

        ttk.Label(input_frame, text="Status:").grid(row=1, column=2, sticky='e', padx=8, pady=8)
        self.order_status = ttk.Combobox(input_frame, values=["Pending", "In Progress", "Completed", "Delivered"], state="readonly", width=16)
        self.order_status.set("Pending")
        self.order_status.grid(row=1, column=3, padx=8, pady=8, sticky='ew')

        # Row 2: Paid Checkbox
        self.order_is_paid_var = tk.BooleanVar(value=False)
        self.order_paid_chk = ttk.Checkbutton(input_frame, text="Paid in Full", variable=self.order_is_paid_var)
        self.order_paid_chk.grid(row=2, column=0, columnspan=2, padx=8, pady=5, sticky='w')

        # Sub-Frame for Multiple Order Items 
        items_frame = ttk.LabelFrame(input_frame, text="Order Items (Descriptions & Prices)")
        items_frame.grid(row=3, column=0, columnspan=4, sticky='ew', padx=8, pady=10)
        items_frame.columnconfigure(1, weight=1)

        ttk.Label(items_frame, text="Description:").grid(row=0, column=0, padx=6, pady=6, sticky='e')
        self.item_desc_entry = ttk.Entry(items_frame, width=28)
        self.item_desc_entry.grid(row=0, column=1, padx=6, pady=6, sticky='ew')

        ttk.Label(items_frame, text="Price (GHC):").grid(row=0, column=2, padx=6, pady=6, sticky='e')
        self.item_price_entry = ttk.Entry(items_frame, width=10)
        self.item_price_entry.grid(row=0, column=3, padx=6, pady=6, sticky='w')

        ttk.Button(items_frame, text="Add Item", command=self.add_item_to_order).grid(row=0, column=4, padx=6, pady=6)

        # Mini-Treeview to display items added to the current order
        columns_item = ("Description", "Price")
        self.items_tree = ttk.Treeview(items_frame, columns=columns_item, show='headings', height=3)
        self.items_tree.heading("Description", text="Item Description")
        self.items_tree.heading("Price", text="Price (GHC)")
        self.items_tree.column("Description", width=260)
        self.items_tree.column("Price", width=90, anchor='center')
        self.items_tree.grid(row=1, column=0, columnspan=5, padx=6, pady=6, sticky='ew')

        # Remove Item button & Total Label Frame
        ttk.Button(items_frame, text="Remove Selected Item", command=self.remove_item_from_order).grid(row=2, column=0, columnspan=2, padx=6, pady=6, sticky='w')

        # Total Price Label
        self.total_label = ttk.Label(items_frame, text="Total: GHC 0.00", font=("Helvetica", 10, "bold"))
        self.total_label.grid(row=2, column=2, columnspan=3, padx=6, pady=6, sticky='e')

        # Action Buttons Frame
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=4, column=0, columnspan=4, pady=10)

        self.save_order_btn = ttk.Button(btn_frame, text="Save Order", command=self.save_or_update_order)
        self.save_order_btn.pack(side='left', padx=6)

        ttk.Button(btn_frame, text="Clear Fields", command=self.clear_order_fields).pack(side='left', padx=6)

        # 2. Compact Actions Bar (Search, Filter, Sort & Reset)
        actions_bar = ttk.Frame(orders_master_page)
        actions_bar.pack(anchor='center', padx=8, pady=8)

        ttk.Button(actions_bar, text="Search Orders", command=self.open_search_popup).pack(side='left', padx=5)
        ttk.Button(actions_bar, text="Filter by Status", command=self.open_filter_popup).pack(side='left', padx=5)
        ttk.Button(actions_bar, text="Sort Days Left", command=self.open_sort_popup).pack(side='left', padx=5)
        ttk.Button(actions_bar, text="Show All / Reset", command=self.refresh_treeview).pack(side='left', padx=5)

        # 3. Main Treeview for All Orders (Stretched full width)
        main_columns = ("ID", "Client", "Phone", "Items Summary", "Total Price", "Paid", "Status", "Due Date", "Days Left")
        self.tree = ttk.Treeview(orders_master_page, columns=main_columns, show='headings', height=10)
        
        for col in main_columns:
            self.tree.heading(col, text=col)
        
        self.tree.column("ID", width=35, anchor='center')
        self.tree.column("Client", width=120)
        self.tree.column("Phone", width=110, anchor='center')
        self.tree.column("Items Summary", width=190)
        self.tree.column("Total Price", width=90, anchor='center')
        self.tree.column("Paid", width=65, anchor='center')
        self.tree.column("Status", width=95, anchor='center')
        self.tree.column("Due Date", width=95, anchor='center')
        self.tree.column("Days Left", width=105, anchor='center')

        self.tree.pack(padx=8, pady=8, fill='x', expand=True)
        
        # Bind selecting an order in the main table to load it for editing
        self.tree.bind("<<TreeviewSelect>>", self.load_order_into_form)
        self.tree.tag_configure('overdue', background='#ffcccc')

        # 4. Bottom Action Buttons Frame
        bottom_btn_frame = ttk.Frame(orders_master_page)
        bottom_btn_frame.pack(anchor='center', pady=8)

        ttk.Button(bottom_btn_frame, text="Delete Selected Order", command=self.delete_order).pack(side='left', padx=12)
        ttk.Button(bottom_btn_frame, text="Export Orders to CSV", command=self.export_orders_to_csv).pack(side='left', padx=12)

    def open_search_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Search Orders by Client Name")
        self.center_window(popup, 360, 150)
        popup.transient(self.root)
        popup.grab_set()
        
        ttk.Label(popup, text="Enter Client Name:", font=("Helvetica", 10, "bold")).pack(pady=10)
        search_entry = ttk.Entry(popup, width=32)
        search_entry.pack(pady=5)
        search_entry.focus()
        
        def execute():
            query = search_entry.get().strip()
            if not query:
                messagebox.showwarning("Input Error", "Please enter a client name.", parent=popup)
                return
            popup.destroy()
            self.search_orders_query(query)
            
        ttk.Button(popup, text="Search", command=execute).pack(pady=10)

    def open_filter_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Filter Orders by Status")
        self.center_window(popup, 320, 160)
        popup.transient(self.root)
        popup.grab_set()
        
        ttk.Label(popup, text="Select Order Status:", font=("Helvetica", 10, "bold")).pack(pady=10)
        combo = ttk.Combobox(popup, values=["All", "Pending", "In Progress", "Completed", "Delivered"], state="readonly", width=25)
        combo.set(self.current_status_filter)
        combo.pack(pady=5)
        
        def execute():
            selected_status = combo.get()
            self.current_status_filter = selected_status
            popup.destroy()
            self.filter_by_status(selected_status)
            
        ttk.Button(popup, text="Apply Filter", command=execute).pack(pady=10)

    def open_sort_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Sort Orders")
        self.center_window(popup, 360, 160)
        popup.transient(self.root)
        popup.grab_set()
        
        ttk.Label(popup, text="Sort by Due Days Left:", font=("Helvetica", 10, "bold")).pack(pady=10)
        combo = ttk.Combobox(popup, values=["Ascending (Fewest Days First)", "Descending (Most Days First)"], state="readonly", width=32)
        combo.set("Ascending (Fewest Days First)")
        combo.pack(pady=5)
        
        def execute():
            choice = combo.get()
            popup.destroy()
            self.sort_due_date_action(choice)
            
        ttk.Button(popup, text="Apply Sort", command=execute).pack(pady=10)

    def search_orders_query(self, query):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.cursor.execute("""
            SELECT id, client_name, phone_number, total_price, status, due_date, items_json, is_paid 
            FROM orders 
            WHERE client_name LIKE ? 
            ORDER BY id DESC
        """, (f'%{query}%',))
        
        rows = self.cursor.fetchall()
        if not rows:
            messagebox.showinfo("Not Found", "No orders found matching that client name.")
            self.refresh_treeview()
            return

        self.populate_order_tree(rows)

    def filter_by_status(self, selected_status):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if selected_status == "All":
            self.cursor.execute("SELECT id, client_name, phone_number, total_price, status, due_date, items_json, is_paid FROM orders ORDER BY id DESC")
        else:
            self.cursor.execute("""
                SELECT id, client_name, phone_number, total_price, status, due_date, items_json, is_paid 
                FROM orders 
                WHERE status = ? 
                ORDER BY id DESC
            """, (selected_status,))
            
        rows = self.cursor.fetchall()
        if not rows:
            messagebox.showinfo("Result", f"No orders found with status '{selected_status}'.")
        self.populate_order_tree(rows)

    def sort_due_date_action(self, sort_choice):
        reverse = True if "Descending" in sort_choice else False
        today = datetime.now().date()
        
        def get_days_left(item_id):
            due_str = self.tree.set(item_id, "Due Date")
            try:
                due_date_obj = datetime.strptime(due_str, "%Y-%m-%d").date()
                return (due_date_obj - today).days
            except ValueError:
                return float('inf')
        
        item_ids = list(self.tree.get_children(''))
        item_ids.sort(key=get_days_left, reverse=reverse)
        
        for index, k in enumerate(item_ids):
            self.tree.move(k, '', index)

    def export_orders_to_csv(self):
        item_ids = self.tree.get_children()
        if not item_ids:
            messagebox.showwarning("Export Warning", "There are no orders currently displayed to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Orders to CSV"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Order ID", "Client Name", "Phone Number", "Items Summary", "Total Price", "Paid in Full", "Status", "Due Date"])
                
                for item_id in item_ids:
                    values = self.tree.item(item_id, 'values')
                    order_id, name, phone, summary, total_price, paid_str, status, due, _ = values
                    writer.writerow([order_id, name, phone, summary, total_price, paid_str, status, due])
                    
            messagebox.showinfo("Success", f"Displayed orders exported successfully to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def add_item_to_order(self):
        desc = self.item_desc_entry.get().strip()
        price_str = self.item_price_entry.get().strip()

        if not desc:
            messagebox.showwarning("Input Error", "Please enter an item description.")
            return
        
        try:
            price = float(price_str) if price_str else 0.0
        except ValueError:
            messagebox.showwarning("Input Error", "Price must be a valid number.")
            return

        self.current_order_items.append({"desc": desc, "price": price})
        self.refresh_current_items_display()

        self.item_desc_entry.delete(0, tk.END)
        self.item_price_entry.delete(0, tk.END)

    def remove_item_from_order(self):
        selected = self.items_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select an item from the list to remove.")
            return
        idx = int(selected[0])
        del self.current_order_items[idx]
        self.refresh_current_items_display()

    def refresh_current_items_display(self):
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)

        total = 0.0
        for idx, item in enumerate(self.current_order_items):
            self.items_tree.insert("", tk.END, iid=str(idx), values=(item["desc"], f"{item['price']:.2f}"))
            total += item["price"]

        self.total_label.config(text=f"Total: GHC {total:.2f}")

    def save_measurements(self):
        name = self.meas_name.get().strip()
        gender = self.meas_gender.get()
        
        if not name:
            messagebox.showwarning("Input Error", "Client Name is required!")
            return

        data = {m: self.meas_entries[m].get() for m in self.meas_entries}
        data_json = json.dumps(data)

        try:
            if self.current_meas_id is None:
                self.cursor.execute("SELECT id FROM measurements WHERE client_name = ?", (name,))
                if self.cursor.fetchone():
                    messagebox.showwarning("Duplicate Error", "A customer with this full name already exists!")
                    return

                self.cursor.execute("SELECT MAX(id) FROM measurements")
                res = self.cursor.fetchone()
                next_id = (res[0] or 0) + 1

                self.cursor.execute("INSERT INTO measurements (id, client_name, gender, measurements_data) VALUES (?, ?, ?, ?)",
                                    (next_id, name, gender, data_json))
                messagebox.showinfo("Success", "Measurements saved successfully!")
            else:
                self.cursor.execute("SELECT id FROM measurements WHERE client_name = ? AND id != ?", (name, self.current_meas_id))
                if self.cursor.fetchone():
                    messagebox.showwarning("Duplicate Error", "Another customer with this full name already exists!")
                    return

                self.cursor.execute("UPDATE measurements SET client_name=?, gender=?, measurements_data=? WHERE id=?",
                                    (name, gender, data_json, self.current_meas_id))
                messagebox.showinfo("Success", "Measurements updated successfully!")

            self.conn.commit()
            self.clear_measurement_form()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def delete_measurements(self):
        if self.current_meas_id is None:
            messagebox.showwarning("Selection Error", "Please load a client's measurements to delete first.")
            return

        name = self.meas_name.get().strip()
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete measurements for '{name}'?"):
            try:
                self.cursor.execute("DELETE FROM measurements WHERE id=?", (self.current_meas_id,))
                
                self.cursor.execute("SELECT client_name, gender, measurements_data FROM measurements ORDER BY id ASC")
                remaining = self.cursor.fetchall()
                self.cursor.execute("DELETE FROM measurements")
                for new_id, row in enumerate(remaining, start=1):
                    self.cursor.execute(
                        "INSERT INTO measurements (id, client_name, gender, measurements_data) VALUES (?, ?, ?, ?)",
                        (new_id, row[0], row[1], row[2])
                    )
                
                self.conn.commit()
                messagebox.showinfo("Success", "Client measurements deleted successfully!")
                self.clear_measurement_form()
            except Exception as e:
                messagebox.showerror("Database Error", str(e))

    def search_measurements(self):
        query = self.meas_search_entry.get().strip()
        if not query:
            messagebox.showwarning("Input Error", "Please enter a client name to search.")
            return

        self.cursor.execute("SELECT id, client_name, gender FROM measurements WHERE client_name LIKE ?", 
                            (f'%{query}%',))
        results = self.cursor.fetchall()

        if not results:
            messagebox.showinfo("Not Found", "No measurements found for that client name.")
            return

        if len(results) == 1:
            self.load_measurement_data(results[0][0])
        else:
            self.show_selection_popup(results)

    def view_all_clients(self):
        self.cursor.execute("SELECT id, client_name, gender FROM measurements ORDER BY client_name")
        results = self.cursor.fetchall()

        if not results:
            messagebox.showinfo("Client Directory", "No clients found in the database.")
            return

        popup = tk.Toplevel(self.root)
        popup.title("All Clients Directory")
        self.center_window(popup, 460, 360)
        popup.transient(self.root)
        popup.grab_set()
        
        ttk.Label(popup, text="All Saved Clients (Double-click to load into form)", font=("Helvetica", 11, "bold")).pack(pady=10)
        
        columns = ("ID", "Name", "Gender")
        tree = ttk.Treeview(popup, columns=columns, show='headings', selectmode="browse")
        tree.heading("ID", text="ID")
        tree.heading("Name", text="Client Name")
        tree.heading("Gender", text="Gender")
        
        tree.column("ID", width=40, anchor='center')
        tree.column("Name", width=250)
        tree.column("Gender", width=120, anchor='center')
        
        tree.pack(expand=True, fill='both', padx=10, pady=5)

        for meas_id, name, gender in results:
            tree.insert("", tk.END, iid=str(meas_id), values=(meas_id, name, gender or ""))
            
        def load_selected():
            selected = tree.selection()
            if selected:
                meas_id = int(selected[0])
                self.load_measurement_data(meas_id)
                popup.destroy()
            else:
                messagebox.showwarning("Selection Error", "Please select a client to load.")

        def delete_selected():
            selected = tree.selection()
            if selected:
                meas_id = int(selected[0])
                name = tree.item(selected[0])['values'][1]
                if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete measurements for '{name}'?"):
                    try:
                        self.cursor.execute("DELETE FROM measurements WHERE id=?", (meas_id,))
                        self.cursor.execute("SELECT client_name, gender, measurements_data FROM measurements ORDER BY id ASC")
                        remaining = self.cursor.fetchall()
                        self.cursor.execute("DELETE FROM measurements")
                        for new_id, row in enumerate(remaining, start=1):
                            self.cursor.execute(
                                "INSERT INTO measurements (id, client_name, gender, measurements_data) VALUES (?, ?, ?, ?)",
                                (new_id, row[0], row[1], row[2])
                            )
                        self.conn.commit()
                        popup.destroy()
                        self.view_all_clients()
                        if self.current_meas_id == meas_id:
                            self.clear_measurement_form()
                        messagebox.showinfo("Success", "Client measurements deleted successfully!")
                    except Exception as e:
                        messagebox.showerror("Database Error", str(e))
            else:
                messagebox.showwarning("Selection Error", "Please select a client to delete.")

        btn_frame = ttk.Frame(popup)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Load into Form", command=load_selected).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete Client", command=delete_selected).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Close", command=popup.destroy).pack(side='left', padx=5)

        tree.bind("<Double-1>", lambda event: load_selected())

    def show_selection_popup(self, results):
        popup = tk.Toplevel(self.root)
        popup.title("Select Client")
        self.center_window(popup, 320, 260)
        popup.transient(self.root)
        popup.grab_set()
        
        ttk.Label(popup, text="Multiple clients found. Single-click one to load:", font=("Helvetica", 10, "bold")).pack(pady=10)
        
        columns = ("Name",)
        tree = ttk.Treeview(popup, columns=columns, show='headings', selectmode="browse")
        tree.heading("Name", text="Client Name")
        tree.column("Name", width=280)
        tree.pack(expand=True, fill='both', padx=10, pady=5)

        for meas_id, name, gender in results:
            tree.insert("", tk.END, iid=str(meas_id), values=(name,))
            
        def on_row_click(event):
            item = tree.identify_row(event.y)
            if item:
                self.load_measurement_data(int(item))
                popup.destroy()

        tree.bind("<ButtonRelease-1>", on_row_click)

    def load_measurement_data(self, meas_id):
        self.cursor.execute("SELECT client_name, gender, measurements_data FROM measurements WHERE id=?", (meas_id,))
        result = self.cursor.fetchone()
        
        if result:
            self.clear_measurement_form()
            self.current_meas_id = int(meas_id)
            
            self.meas_name.insert(0, result[0])
            self.meas_gender.set(result[1])
            
            data = json.loads(result[2])
            for m in self.meas_entries:
                if m in data:
                    self.meas_entries[m].insert(0, data[m])

    def clear_measurement_form(self):
        self.current_meas_id = None
        self.meas_name.delete(0, tk.END)
        self.meas_gender.set("Select")
        for m in self.meas_entries:
            self.meas_entries[m].delete(0, tk.END)

    def save_or_update_order(self):
        name = self.order_client_name.get().strip()
        phone = self.order_client_phone.get().strip()
        status = self.order_status.get()
        due = self.order_due_date.get().strip()
        is_paid = 1 if self.order_is_paid_var.get() else 0

        if not name or not due:
            messagebox.showwarning("Input Error", "Client Name and Due Date are required!")
            return

        try:
            datetime.strptime(due, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning(
                "Invalid Date", 
                "Please enter a valid date in YYYY-MM-DD format (e.g., 2026-12-25)."
            )
            return

        if not self.current_order_items:
            messagebox.showwarning("Input Error", "Please add at least one order item description and price!")
            return

        total_price = sum(item["price"] for item in self.current_order_items)
        items_json = json.dumps(self.current_order_items)

        if self.current_order_id is None:
            self.cursor.execute("SELECT MAX(id) FROM orders")
            res = self.cursor.fetchone()
            next_id = (res[0] or 0) + 1

            self.cursor.execute(
                "INSERT INTO orders (id, client_name, phone_number, status, due_date, items_json, total_price, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (next_id, name, phone, status, due, items_json, f"{total_price:.2f}", is_paid)
            )
            messagebox.showinfo("Success", "Order added successfully!")
        else:
            self.cursor.execute("UPDATE orders SET client_name=?, phone_number=?, status=?, due_date=?, items_json=?, total_price=?, is_paid=? WHERE id=?",
                                (name, phone, status, due, items_json, f"{total_price:.2f}", is_paid, self.current_order_id))
            messagebox.showinfo("Success", "Order updated successfully!")
            
        self.conn.commit()
        self.refresh_treeview()
        self.clear_order_fields()

    def load_order_into_form(self, event):
        selected = self.tree.selection()
        if not selected:
            return
            
        values = self.tree.item(selected[0])['values']
        if values:
            order_id = values[0]
            self.current_order_id = order_id
            
            self.cursor.execute("SELECT client_name, phone_number, status, due_date, items_json, is_paid FROM orders WHERE id=?", (order_id,))
            row = self.cursor.fetchone()
            if row:
                self.order_client_name.delete(0, tk.END)
                self.order_client_name.insert(0, row[0])
                
                self.order_client_phone.delete(0, tk.END)
                self.order_client_phone.insert(0, row[1] if row[1] else "")
                
                self.order_status.set(row[2])
                
                self.order_due_date.delete(0, tk.END)
                self.order_due_date.insert(0, row[3])
                
                self.current_order_items = json.loads(row[4]) if row[4] else []
                self.refresh_current_items_display()

                self.order_is_paid_var.set(bool(row[5]))

                self.save_order_btn.config(text="Update Order")

    def clear_order_fields(self):
        self.current_order_id = None
        self.current_order_items = []
        self.order_client_name.delete(0, tk.END)
        self.order_client_phone.delete(0, tk.END)
        self.order_due_date.delete(0, tk.END)
        self.order_status.set("Pending")
        self.order_is_paid_var.set(False)
        self.item_desc_entry.delete(0, tk.END)
        self.item_price_entry.delete(0, tk.END)
        self.refresh_current_items_display()
        self.save_order_btn.config(text="Save Order")
        
        for item in self.tree.selection():
            self.tree.selection_remove(item)

    def refresh_treeview(self):
        self.current_status_filter = "All"
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.cursor.execute("SELECT id, client_name, phone_number, total_price, status, due_date, items_json, is_paid FROM orders ORDER BY id DESC")
        rows = self.cursor.fetchall()
        self.populate_order_tree(rows)

    def populate_order_tree(self, rows):
        for row in rows:
            order_id, name, phone, total_price, status, due, items_json, is_paid = row
            
            summary = ""
            if items_json:
                try:
                    items = json.loads(items_json)
                    summary = ", ".join([i['desc'] for i in items])
                except:
                    pass

            paid_str = "Yes" if is_paid else "No"
            phone_str = phone if phone else ""
            days_left_str = ""
            tags = ()
            
            if status == "Delivered":
                days_left_str = "—"
            else:
                try:
                    due_date_obj = datetime.strptime(due, "%Y-%m-%d").date()
                    today = datetime.now().date()
                    delta = (due_date_obj - today).days

                    if delta > 0:
                        days_left_str = f"{delta} day{'s' if delta > 1 else ''} left"
                    elif delta == 0:
                        days_left_str = "Due Today"
                    else:
                        days_left_str = f"Overdue ({abs(delta)}d)"
                        if status != "Completed":
                            tags = ('overdue',)
                except ValueError:
                    days_left_str = "Invalid Date"
                
            self.tree.insert("", tk.END, values=(order_id, name, phone_str, summary, f"GHC {total_price}" if total_price else "", paid_str, status, due, days_left_str), tags=tags)

    def delete_order(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "Please select an order to delete.")
            return
            
        order_id = self.tree.item(selected[0])['values'][0]
        try:
            self.cursor.execute("DELETE FROM orders WHERE id=?", (order_id,))
            
            self.cursor.execute("SELECT client_name, phone_number, status, due_date, items_json, total_price, is_paid FROM orders ORDER BY id ASC")
            remaining = self.cursor.fetchall()
            self.cursor.execute("DELETE FROM orders")
            for new_id, row in enumerate(remaining, start=1):
                self.cursor.execute(
                    "INSERT INTO orders (id, client_name, phone_number, status, due_date, items_json, total_price, is_paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (new_id, row[0], row[1], row[2], row[3], row[4], row[5], row[6])
                )
            
            self.conn.commit()
            self.refresh_treeview()
            self.clear_order_fields()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = TailorApp(root)
    root.mainloop()