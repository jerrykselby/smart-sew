# SmartSew: Tailoring & Order Management System

A custom desktop application designed to digitize and streamline boutique workflows, replacing traditional paper notebooks with a robust, offline-first solution.

## The Inspiration
This project started at my tailor’s shop, where I watched him spend several minutes flipping frantically through dozens of pages in a heavy notebook just to find my measurements from months ago. Realizing how much administrative friction local businesses face, I built this application to bring digital efficiency to traditional craftsmanship.

## Key Features

* **Dynamic Order Management:** Track client details, payment status, and multi-item orders with automated running totals (in GHC).
* **Smart Deadline Tracking:** Real-time delivery countdowns with automated color-coded alerts (`#ffcccc`) for overdue orders.
* **Comprehensive Measurement Matrix:** A structured profile builder tracking 19 distinct body dimensions per client.
* **Business Portability:** Built-in search, status filtering, and CSV export for easy record-keeping and offline backups.

## Tech Stack & Architecture

*   **Frontend UI:** Python, `tkinter`, and `ttk` for a lightweight, cross-platform desktop interface.

*   **Database:** SQLite backend with automated schema migration checks (`PRAGMA table_info`) to protect user data safely during updates.

*   **Data Serialization:** Utilizes JSON to cleanly store complex, semi-structured body measurements and multi-item lists within a relational database framework.

## Getting Started
### Prerequisites
Make sure you have Python installed on your machine. (The app uses Python's standard library, so no external package installations are required!).

### Running the Application
1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR-USERNAME/smart-sew.git


2. Navigate into the project directory:
cd smart-sew

3. Run the application:
smart_sew.py

## Video Walkthrough

Check out a quick video demonstration of the app(https://lnkd.in/p/dsxVVgxS)
