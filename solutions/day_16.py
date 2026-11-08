# Day 16 reference solutions: dates and times
import sqlite3
from datetime import date, datetime

from helpers import TODAY, datasets_conn, library_full_conn, shop_conn, show

shop = shop_conn()
lib = library_full_conn()

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
print(shop.execute("SELECT date(?)", (TODAY,)).fetchone())
print(shop.execute("SELECT date('now') > '2025-01-01', length(datetime('now'))").fetchone())  # 'now' really works, but the value changes every day

print("# Level 1, Q2")
print(shop.execute("SELECT date(?, '+30 days')", (TODAY,)).fetchone())

print("# Level 1, Q3")
show(shop.execute("""
    SELECT order_id, order_date,
           CAST(strftime('%Y', order_date) AS INTEGER) AS year,
           CAST(strftime('%m', order_date) AS INTEGER) AS month
    FROM orders ORDER BY order_id LIMIT 5
"""))

print("# Level 1, Q4")
show(shop.execute("""
    SELECT customer_id, first_name, signup_date,
           CAST(julianday(?) - julianday(signup_date) AS INTEGER) AS days_since_signup
    FROM customers ORDER BY customer_id LIMIT 5
""", (TODAY,)))

print("# Level 1, Q5")
print(shop.execute("""
    SELECT CASE strftime('%w', ?) WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday'
           WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday' ELSE 'Saturday' END
""", (TODAY,)).fetchone())

print("# Level 1, Q6")
print(shop.execute("""
    SELECT date(:d, 'start of month'), date(:d, 'start of month', '+1 month', '-1 day'), date(:d, 'start of year')
""", {"d": TODAY}).fetchone())

print("# Level 1, Q7")
print(shop.execute("SELECT date(?, 'weekday 1')", (TODAY,)).fetchone(), shop.execute("SELECT date(?, '+1 day', 'weekday 1')", (TODAY,)).fetchone())

print("# Level 1, Q8")
print(shop.execute("SELECT COUNT(*) FROM orders WHERE strftime('%Y-%m', order_date) = '2025-12'").fetchone(),
      shop.execute("SELECT COUNT(*) FROM orders WHERE order_date >= '2025-12-01' AND order_date < '2026-01-01'").fetchone())

print("# Level 1, Q9")
show(lib.execute("""
    SELECT id, loaned_on, returned_on, CAST(julianday(returned_on) - julianday(loaned_on) AS INTEGER) AS days_kept
    FROM loans WHERE returned_on IS NOT NULL ORDER BY id
"""))

print("# Level 1, Q10")
show(lib.execute("""
    SELECT name, joined_on, CAST(julianday(?) - julianday(joined_on) AS INTEGER) AS days_member
    FROM members ORDER BY joined_on
""", (TODAY,)))

print("# Level 1, Q11")
moment = datetime(2025, 3, 14, 9, 30)
iso = moment.isoformat(sep=" ")
print(iso, shop.execute("SELECT datetime(?, '+90 minutes')", (iso,)).fetchone())
back = datetime.fromisoformat(shop.execute("SELECT datetime(?, '+90 minutes')", (iso,)).fetchone()[0])
print(repr(back), date(2025, 3, 14).isoformat())

print("# Level 1, Q12")
print(shop.execute("SELECT date('2025-02-30'), date('2025-02-32'), date('2025-13-01'), date('14/03/2025')").fetchone())

print("# Level 1, Q13")
print(shop.execute("SELECT unixepoch(?), datetime(unixepoch(?), 'unixepoch')", (TODAY, TODAY)).fetchone())

print("# Level 1, Q14")
print(shop.execute("SELECT timediff('2025-03-14 12:00:00', '2025-03-13 10:30:00')").fetchone(),
      shop.execute("SELECT (unixepoch('2025-03-14 12:00:00') - unixepoch('2025-03-13 10:30:00')) / 60").fetchone())

print("# Level 1, Q15")
# ISO 8601 puts the biggest unit first (year, month, day, hour...), so comparing the TEXT left to right is the same as comparing the time.

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
show(shop.execute("""
    SELECT strftime('%Y-%m', order_date) AS month, COUNT(*) AS orders
    FROM orders
    WHERE order_date >= '2025-01-01' AND order_date < '2026-01-01'
    GROUP BY month ORDER BY month
"""))

print("# Level 2, Q2")
print(shop.execute("""
    SELECT COUNT(*), ROUND(AVG(julianday(f.first_order) - julianday(c.signup_date)), 1)
    FROM customers AS c
    JOIN (SELECT customer_id, MIN(order_date) AS first_order FROM orders GROUP BY customer_id) AS f
      ON f.customer_id = c.customer_id
""").fetchone())

print("# Level 2, Q3")
show(lib.execute("""
    SELECT l.id, b.title, m.name AS member, l.due_on,
           CAST(julianday(?) - julianday(l.due_on) AS INTEGER) AS days_overdue
    FROM loans AS l
    JOIN books AS b ON b.id = l.book_id
    JOIN members AS m ON m.id = l.member_id
    WHERE l.returned_on IS NULL AND l.due_on < ?
    ORDER BY days_overdue DESC, l.id
""", (TODAY, TODAY)))
show(lib.execute("""
    SELECT l.id, b.title, l.due_on, l.returned_on,
           CAST(julianday(l.returned_on) - julianday(l.due_on) AS INTEGER) AS days_late
    FROM loans AS l JOIN books AS b ON b.id = l.book_id
    WHERE l.returned_on > l.due_on
"""))
# loan period check: due_on is always loaned_on + 14 days
print(lib.execute("SELECT COUNT(*) FROM loans WHERE due_on <> date(loaned_on, '+14 days')").fetchone())

print("# Level 2, Q4")
show(shop.execute("""
    SELECT CASE strftime('%w', order_date) WHEN '0' THEN 'Sun' WHEN '1' THEN 'Mon' WHEN '2' THEN 'Tue' WHEN '3' THEN 'Wed'
                                           WHEN '4' THEN 'Thu' WHEN '5' THEN 'Fri' ELSE 'Sat' END AS weekday,
           COUNT(*) AS orders
    FROM orders
    GROUP BY strftime('%w', order_date)
    ORDER BY strftime('%w', order_date)
"""))

print("# Level 2, Q5")
show(shop.execute("""
    SELECT customer_id, first_name, last_name, signup_date
    FROM customers
    WHERE signup_date >= date(?, '-90 days')
    ORDER BY signup_date, customer_id
""", (TODAY,)))
print(date.fromisoformat(TODAY).isoformat())

print("# Level 2, Q6")
show(shop.execute("""
    SELECT 'Q' || ((CAST(strftime('%m', o.order_date) AS INTEGER) - 1) / 3 + 1) AS quarter,
           format('%.2f', SUM(i.quantity * i.unit_price_cents) / 100.0) AS revenue
    FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
    WHERE o.status <> 'cancelled' AND o.order_date >= '2025-01-01' AND o.order_date < '2026-01-01'
    GROUP BY quarter ORDER BY quarter
"""))

print("# Level 2, Q7")
# Python side: pass ISO strings, never datetime objects
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, at TEXT NOT NULL) STRICT")
conn.execute("INSERT INTO events (at) VALUES (?)", (datetime(2025, 3, 14, 18, 45).isoformat(sep=" ", timespec="seconds"),))
conn.execute("INSERT INTO events (at) VALUES (?)", (date(2025, 3, 15).isoformat() + " 08:00:00",))
rows = conn.execute("SELECT at FROM events ORDER BY at").fetchall()
print(rows)
print([datetime.fromisoformat(r[0]) for r in rows])

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1")
hn = datasets_conn()
iso_cte = """
    WITH p1 AS (
        SELECT id, num_points, created_at,
               substr(created_at, 1, instr(created_at, '/') - 1) AS m,
               substr(created_at, instr(created_at, '/') + 1)    AS rest
        FROM hn_posts
    ),
    p2 AS (
        SELECT id, num_points, m,
               substr(rest, 1, instr(rest, '/') - 1)             AS d,
               substr(rest, instr(rest, '/') + 1)                AS rest2
        FROM p1
    ),
    p3 AS (
        SELECT id, num_points, m, d,
               substr(rest2, 1, 4)                               AS y,
               substr(rest2, 6)                                  AS hm
        FROM p2
    ),
    posts AS (
        SELECT id, num_points,
               y || '-' || printf('%02d', m) || '-' || printf('%02d', d) || ' '
                 || printf('%02d', substr(hm, 1, instr(hm, ':') - 1)) || ':' || substr(hm, instr(hm, ':') + 1) || ':00' AS created_iso
        FROM p3
    )
"""
show(hn.execute(iso_cte + "SELECT id, created_iso FROM posts ORDER BY id LIMIT 4"))
show(hn.execute(iso_cte + """
    SELECT CAST(strftime('%H', created_iso) AS INTEGER) AS hour, COUNT(*) AS posts, ROUND(AVG(num_points), 2) AS avg_points
    FROM posts
    GROUP BY hour
    ORDER BY avg_points DESC, hour
    LIMIT 5
"""))
print(hn.execute(iso_cte + "SELECT MIN(created_iso), MAX(created_iso), COUNT(created_iso) FROM posts").fetchone())
# the Python way, converting while loading
t = datetime.strptime("8/4/2016 11:52", "%m/%d/%Y %H:%M")
print(t.isoformat(sep=" "))

print("# Level 3, Q2")
show(hn.execute(iso_cte + """
    SELECT CASE strftime('%w', created_iso) WHEN '0' THEN 'Sun' WHEN '1' THEN 'Mon' WHEN '2' THEN 'Tue' WHEN '3' THEN 'Wed'
                                            WHEN '4' THEN 'Thu' WHEN '5' THEN 'Fri' ELSE 'Sat' END AS weekday,
           COUNT(*) AS posts, ROUND(AVG(num_points), 2) AS avg_points
    FROM posts
    GROUP BY strftime('%w', created_iso)
    ORDER BY avg_points DESC
"""))

print("# Level 3, Q3")
show(shop.execute("""
    WITH first_orders AS (
        SELECT customer_id, MIN(order_date) AS first_order FROM orders GROUP BY customer_id
    )
    SELECT strftime('%Y-%m', c.signup_date) AS cohort,
           COUNT(*) AS customers,
           COUNT(f.customer_id) AS ordered,
           COUNT(*) FILTER (WHERE julianday(f.first_order) - julianday(c.signup_date) <= 90) AS within_90_days
    FROM customers AS c
    LEFT JOIN first_orders AS f ON f.customer_id = c.customer_id
    GROUP BY cohort
    ORDER BY cohort
    LIMIT 8
"""))
print(shop.execute("""
    SELECT COUNT(DISTINCT strftime('%Y-%m', signup_date)) FROM customers
""").fetchone())
