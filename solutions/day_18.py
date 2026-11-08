# Day 18 reference solutions
# Day 18 reference solutions
import sqlite3
from datetime import datetime

from helpers import DATA, datasets_conn, library_full_conn, show


def shop():
    """In-memory copy of data/shop.db (students use sqlite3.connect('data/shop.db'))."""
    src = sqlite3.connect(DATA / "shop.db")
    dst = sqlite3.connect(":memory:")
    src.backup(dst)
    src.close()
    return dst


conn = shop()
lib = library_full_conn()

print("# L1Q1")
show(conn.execute('''
    WITH daily AS (
        SELECT o.order_date AS day, SUM(oi.quantity * oi.unit_price_cents) AS cents
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY o.order_date
    )
    SELECT day, cents, SUM(cents) OVER (ORDER BY day) AS running_cents
    FROM daily
    ORDER BY day
    LIMIT 5
'''))

print("# L1Q2")
show(conn.execute('''
    WITH monthly AS (
        SELECT strftime('%Y-%m', order_date) AS month, COUNT(*) AS orders
        FROM orders
        GROUP BY month
    )
    SELECT month, orders, SUM(orders) OVER (ORDER BY month) AS running_orders
    FROM monthly
    ORDER BY month
    LIMIT 5
'''))

print("# L1Q3")
show(conn.execute('''
    WITH x AS (
        SELECT customer_id, order_id, order_date,
               LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date, order_id) AS prev_order
        FROM orders
    )
    SELECT order_id, order_date, prev_order
    FROM x
    WHERE customer_id = 7
    ORDER BY order_date, order_id
    LIMIT 6
'''))

print("# L1Q4")
show(conn.execute('''
    WITH x AS (
        SELECT customer_id, order_id, order_date,
               LEAD(order_date, 1, 'none') OVER (PARTITION BY customer_id ORDER BY order_date, order_id) AS next_order
        FROM orders
    )
    SELECT order_id, order_date, next_order
    FROM x
    WHERE customer_id = 7
    ORDER BY order_date DESC, order_id DESC
    LIMIT 3
'''))

print("# L1Q5")
show(conn.execute('''
    WITH monthly AS (
        SELECT strftime('%Y-%m', o.order_date) AS month, SUM(oi.quantity * oi.unit_price_cents) AS cents
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY month
    )
    SELECT month, cents, cents - LAG(cents) OVER (ORDER BY month) AS change_cents
    FROM monthly
    ORDER BY month
    LIMIT 5
'''))

print("# L1Q6")
show(conn.execute('''
    WITH order_totals AS (
        SELECT o.customer_id, o.order_id, o.order_date, SUM(oi.quantity * oi.unit_price_cents) AS cents
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY o.order_id
    ), running AS (
        SELECT *, SUM(cents) OVER (PARTITION BY customer_id ORDER BY order_date, order_id) AS running_cents
        FROM order_totals
    )
    SELECT order_id, order_date, cents, running_cents
    FROM running
    WHERE customer_id = 3
    ORDER BY order_date, order_id
'''))

print("# L1Q7")
show(conn.execute('''
    WITH order_totals AS (
        SELECT o.customer_id, o.order_id, o.order_date, SUM(oi.quantity * oi.unit_price_cents) AS cents
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled' AND o.customer_id = 3
        GROUP BY o.order_id
    )
    SELECT order_id, order_date, cents,
           MAX(cents) OVER (ORDER BY order_date, order_id) AS best_so_far
    FROM order_totals
    ORDER BY order_date, order_id
'''))

print("# L1Q8")
show(conn.execute('''
    SELECT order_id, order_date,
           FIRST_VALUE(order_date) OVER w AS first_order,
           CAST(julianday(order_date) - julianday(FIRST_VALUE(order_date) OVER w) AS INTEGER) AS days_since_first
    FROM orders
    WHERE customer_id = 3
    WINDOW w AS (ORDER BY order_date, order_id)
    ORDER BY order_date, order_id
'''))

print("# L1Q9")
show(conn.execute('''
    SELECT order_id, order_date,
           LAST_VALUE(order_date) OVER (ORDER BY order_date, order_id) AS wrong,
           LAST_VALUE(order_date) OVER (
               ORDER BY order_date, order_id
               ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
           ) AS right
    FROM orders
    WHERE customer_id = 3
    ORDER BY order_date, order_id
    LIMIT 3
'''))
# wrong: the default frame ends at the current row, so the "last row of the frame" is the current row itself.

print("# L1Q10")
show(conn.execute('''
    WITH monthly AS (
        SELECT strftime('%Y-%m', o.order_date) AS month, SUM(oi.quantity * oi.unit_price_cents) AS cents
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY month
    )
    SELECT month, cents,
           cents - LAG(cents) OVER w AS change_cents,
           SUM(cents) OVER w AS running_cents
    FROM monthly
    WINDOW w AS (ORDER BY month)
    ORDER BY month
    LIMIT 3
'''))

print("# L1Q11")
show(conn.execute('''
    SELECT name, hire_date, salary_cents / 100 AS salary,
           LAG(salary_cents / 100) OVER (ORDER BY hire_date, employee_id) AS prev_salary,
           salary_cents / 100 - LAG(salary_cents / 100) OVER (ORDER BY hire_date, employee_id) AS diff
    FROM employees
    ORDER BY hire_date, employee_id
    LIMIT 6
'''))

print("# L1Q12")
show(lib.execute('''
    SELECT m.name, l.loaned_on,
           LAG(l.loaned_on) OVER (PARTITION BY l.member_id ORDER BY l.loaned_on, l.id) AS prev_loan
    FROM loans AS l
    JOIN members AS m ON m.id = l.member_id
    ORDER BY m.name, l.loaned_on, l.id
'''))

print("# L1Q13")
show(lib.execute('''
    SELECT title, year, pages,
           SUM(pages) OVER (ORDER BY year, title) AS pages_so_far
    FROM books
    ORDER BY year, title
    LIMIT 5
'''))

print("# L1Q14")
show(lib.execute('''
    SELECT title, year, LEAD(title) OVER (ORDER BY year, title) AS next_title
    FROM books
    ORDER BY year DESC, title DESC
    LIMIT 3
'''))

print("# L1Q15")
t = sqlite3.connect(':memory:')
t.execute('CREATE TABLE vals (n INTEGER, v INTEGER)')
t.executemany('INSERT INTO vals VALUES (?, ?)', [(1, 5), (2, 10), (3, 20), (4, 40)])
show(t.execute('''
    SELECT n, v,
           SUM(v) OVER (ORDER BY n) AS running,
           LAG(v) OVER (ORDER BY n) AS prev,
           LEAD(v) OVER (ORDER BY n) AS next
    FROM vals
    ORDER BY n
'''))

print("# L1Q16")
show(t.execute('''
    SELECT n, v,
           SUM(v) OVER (ORDER BY n ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS moving3,
           SUM(v) OVER (ORDER BY n ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) AS centred
    FROM vals
    ORDER BY n
'''))

print("# L1Q17")
# ROWS counts physical rows: "the 2 rows before this one", even if they are weeks apart.
# RANGE works on the values of the ORDER BY column: "all rows whose value is within 2 of mine", and rows with equal
# values (peers) are treated together. Use ROWS for "the last n records", RANGE (on julianday(date)) for "the last n days",
# especially when some days are missing.

print("# L2Q1")
show(conn.execute('''
    WITH daily AS (
        SELECT o.order_date AS day, SUM(oi.quantity * oi.unit_price_cents) AS cents
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY o.order_date
    ), moving AS (
        SELECT day, cents,
               CAST(round(AVG(cents) OVER (
                   ORDER BY julianday(day)
                   RANGE BETWEEN 6 PRECEDING AND CURRENT ROW
               )) AS INTEGER) AS avg_7d
        FROM daily
    )
    SELECT day, cents, avg_7d
    FROM moving
    WHERE day LIKE '2025-03%'
    ORDER BY day
'''))

print("# L2Q2")
show(conn.execute('''
    WITH gaps AS (
        SELECT customer_id, order_date,
               LAG(order_date) OVER w AS prev_order,
               CAST(julianday(order_date) - julianday(LAG(order_date) OVER w) AS INTEGER) AS gap_days
        FROM orders
        WINDOW w AS (PARTITION BY customer_id ORDER BY order_date, order_id)
    )
    SELECT customer_id, order_date, prev_order, gap_days
    FROM gaps
    WHERE customer_id IN (1, 2)
    ORDER BY customer_id, order_date
    LIMIT 8
'''))
show(conn.execute('''
    WITH gaps AS (
        SELECT customer_id,
               julianday(order_date) - julianday(LAG(order_date) OVER w) AS gap_days
        FROM orders
        WINDOW w AS (PARTITION BY customer_id ORDER BY order_date, order_id)
    )
    SELECT customer_id, COUNT(gap_days) + 1 AS orders, round(AVG(gap_days), 1) AS avg_gap
    FROM gaps
    GROUP BY customer_id
    HAVING COUNT(gap_days) + 1 >= 5
    ORDER BY avg_gap, customer_id
    LIMIT 5
'''))

print("# L2Q3")
show(conn.execute('''
    WITH monthly AS (
        SELECT strftime('%Y-%m', o.order_date) AS month, SUM(oi.quantity * oi.unit_price_cents) AS cents
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY month
    ), growth AS (
        SELECT month, cents,
               LAG(cents) OVER w AS prev_cents,
               round(100.0 * (cents - LAG(cents) OVER w) / NULLIF(LAG(cents) OVER w, 0), 1) AS growth_pct
        FROM monthly
        WINDOW w AS (ORDER BY month)
    )
    SELECT month, cents, prev_cents, growth_pct
    FROM growth
    WHERE month >= '2025-01'
    ORDER BY month
'''))

print("# L2Q4")
show(conn.execute('''
    SELECT DISTINCT customer_id,
           FIRST_VALUE(order_date) OVER w AS first_order,
           LAST_VALUE(order_date) OVER w AS last_order,
           CAST(julianday(LAST_VALUE(order_date) OVER w) - julianday(FIRST_VALUE(order_date) OVER w) AS INTEGER) AS span_days
    FROM orders
    WHERE customer_id <= 5
    WINDOW w AS (PARTITION BY customer_id ORDER BY order_date, order_id
                 ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
    ORDER BY customer_id
'''))

print("# L2Q5")
show(lib.execute('''
    SELECT m.name, l.loaned_on,
           CAST(julianday(l.loaned_on) - julianday(LAG(l.loaned_on) OVER (PARTITION BY l.member_id ORDER BY l.loaned_on, l.id)) AS INTEGER) AS days_since_prev,
           iif(l.returned_on > l.due_on, 1, 0) AS returned_late
    FROM loans AS l
    JOIN members AS m ON m.id = l.member_id
    ORDER BY m.name, l.loaned_on, l.id
'''))

print("# L2Q6")
show(conn.execute('''
    WITH monthly AS (
        SELECT c.name AS category, strftime('%Y-%m', o.order_date) AS month,
               SUM(oi.quantity * oi.unit_price_cents) AS cents
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        JOIN products AS p ON p.product_id = oi.product_id
        JOIN categories AS c ON c.category_id = p.category_id
        WHERE o.status <> 'cancelled' AND o.order_date >= '2025-01-01'
        GROUP BY c.category_id, month
    )
    SELECT category, month, cents,
           SUM(cents) OVER (PARTITION BY category ORDER BY month) AS category_running
    FROM monthly
    ORDER BY category, month
    LIMIT 6
'''))
hn = datasets_conn()

print("# L3Q1")
hn.execute("ALTER TABLE hn_posts ADD COLUMN created_day TEXT")
rows = hn.execute("SELECT rowid, created_at FROM hn_posts").fetchall()
hn.executemany(
    "UPDATE hn_posts SET created_day = ? WHERE rowid = ?",
    [(datetime.strptime(created_at, "%m/%d/%Y %H:%M").date().isoformat(), post_id) for post_id, created_at in rows],
)
show(hn.execute('''
    WITH daily AS (
        SELECT created_day AS day, COUNT(*) AS posts
        FROM hn_posts
        GROUP BY created_day
    )
    SELECT day, posts, SUM(posts) OVER (ORDER BY day) AS cumulative_posts
    FROM daily
    ORDER BY day
    LIMIT 5
'''))
show(hn.execute('''
    WITH daily AS (
        SELECT created_day AS day, COUNT(*) AS posts
        FROM hn_posts
        GROUP BY created_day
    )
    SELECT day AS window_end, date(day, '-6 days') AS window_start,
           SUM(posts) OVER (ORDER BY julianday(day) RANGE BETWEEN 6 PRECEDING AND CURRENT ROW) AS posts_7d
    FROM daily
    ORDER BY posts_7d DESC, day
    LIMIT 3
'''))

print("# L3Q2")
show(hn.execute('''
    WITH ranked AS (
        SELECT author, id, num_points,
               ROW_NUMBER() OVER w AS rn,
               LEAD(num_points) OVER w AS second,
               COUNT(*) OVER (PARTITION BY author) AS posts
        FROM hn_posts
        WINDOW w AS (PARTITION BY author ORDER BY num_points DESC, id)
    )
    SELECT author, posts, num_points AS best, second, num_points - second AS gap
    FROM ranked
    WHERE rn = 1 AND posts >= 10
    ORDER BY gap DESC, author
    LIMIT 5
'''))

print("# L3Q3")
show(conn.execute('''
    WITH days AS (
        SELECT DISTINCT customer_id, order_date FROM orders
    ), keyed AS (
        SELECT customer_id, order_date,
               date(order_date, '-' || ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) || ' days') AS grp
        FROM days
    ), streaks AS (
        SELECT customer_id, MIN(order_date) AS streak_start, MAX(order_date) AS streak_end, COUNT(*) AS days
        FROM keyed
        GROUP BY customer_id, grp
    ), ranked AS (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY days DESC, streak_start) AS rn
        FROM streaks
    )
    SELECT customer_id, streak_start, streak_end, days
    FROM ranked
    WHERE rn = 1
    ORDER BY days DESC, customer_id
    LIMIT 3
'''))
