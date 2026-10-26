# MCA VIVA VOCE PREPARATION GUIDE
## Project: AI-Based Personal Budget Planning & Financial Goal System

This guide prepares you to confidently answer all theoretical, architectural, database, mathematical, machine learning, and security questions during your MCA project presentation and final viva examination.

---

### SECTION 1: ARCHITECTURE & FRAMEWORK CHOICES

#### Q1: Why did you choose Flask instead of Django for this project?
**Answer:**  
Flask is a lightweight micro-framework that adheres to the principle of explicit, modular design. While Django comes with heavy "batteries included" (an auto-generated admin panel and tight ORM coupling), Flask allows granular architectural control. In this academic project, building custom authentication flows with Flask-Login, custom 3NF SQLAlchemy models, and integrating Scikit-Learn/Pandas directly into route controllers demonstrates fundamental software engineering and architectural understanding from scratch.

#### Q2: Explain the architecture of your application.
**Answer:**  
The application adopts a **3-Tier Model-View-Controller (MVC / MTV)** architecture:
1. **Presentation Tier (View):** Built with HTML5, Bootstrap 5, custom CSS, and Chart.js for data visualizations, rendered dynamically via Jinja2 templates.
2. **Application Tier (Controller & Logic):** Python 3 and Flask handling routing, Flask-WTF for form validation/CSRF tokens, Flask-Login for session state, and a pure Service Layer containing financial business logic and Scikit-Learn ML models.
3. **Data Tier (Model):** MySQL 8.0 with InnoDB storage engine managed via SQLAlchemy ORM and Flask-Migrate (Alembic).

#### Q3: What is the Application Factory Pattern (`create_app()`) and why did you use it?
**Answer:**  
The Application Factory pattern constructs the Flask application inside a function rather than as a global singleton. This decouples extension instances (`db`, `migrate`, `login_manager`, `csrf`) from the application instance. Crucially, it allows environment switching: running `create_app("testing")` with an isolated in-memory SQLite database during automated Pytest runs, and `create_app("development")` connected to MySQL during live execution.

---

### SECTION 2: DATABASE DESIGN & SQL

#### Q4: Why did you use `DECIMAL(12, 2)` instead of `FLOAT` or `DOUBLE` for monetary amounts?
**Answer:**  
`FLOAT` and `DOUBLE` use IEEE 754 binary floating-point representation, which cannot precisely represent fractional decimal numbers (e.g., $0.1 + 0.2 = 0.30000000000000004$). Over thousands of financial transactions, accumulated rounding errors cause ledger discrepancies. `DECIMAL(12, 2)` stores numbers as exact fixed-point base-10 digits, guaranteeing 100% precision with zero binary roundoff error.

#### Q5: Is your database normalized? Explain how it achieves Third Normal Form (3NF).
**Answer:**  
Yes, the database strictly satisfies 3NF:
- **1NF:** All table attributes are atomic. There are no repeating groups or comma-separated lists (e.g., each contribution is an individual row in `savings_contributions`).
- **2NF:** Every table has a primary key, and all non-key attributes are fully functionally dependent on the entire primary key (no partial dependencies).
- **3NF:** There are no transitive dependencies between non-key attributes. For example, budget utilization percentages and goal remaining amounts are computed dynamically at query time rather than stored statically, eliminating update anomalies.

#### Q6: Why did you create compound indexes on the `transactions` table?
**Answer:**  
We created a compound index on `(user_id, transaction_date)`. Typical financial queries filter by the logged-in user and a date range:
```sql
SELECT * FROM transactions WHERE user_id = 1 AND transaction_date BETWEEN '2026-10-01' AND '2026-10-31';
```
A compound B-Tree index allows MySQL to perform an index seek in $O(\log n)$ time rather than executing a sequential table scan ($O(n)$) across millions of historical rows.

#### Q7: How did you prevent duplicate budget caps for the same category in the same month?
**Answer:**  
We defined a composite unique constraint in SQLAlchemy:
```python
__table_args__ = (
    db.UniqueConstraint("user_id", "category_id", "month", "year", name="uq_user_category_month_year"),
)
```
This enforces uniqueness at the database engine level, complemented by an application-level check in `create_budget()`.

---

### SECTION 3: CYBERSECURITY & DEFENSIVE DESIGN

#### Q8: How are user passwords secured?
**Answer:**  
Passwords are never stored in plaintext. We utilize `werkzeug.security.generate_password_hash`, which applies **PBKDF2 (Password-Based Key Derivation Function 2)** with SHA-256 and a cryptographically secure random salt with thousands of hash iterations. Even if the database is exposed, the hashes cannot be reversed via precomputed rainbow tables.

#### Q9: What is an Insecure Direct Object Reference (IDOR) and how does your project prevent it?
**Answer:**  
An IDOR vulnerability occurs when an application exposes a database record's internal ID in a URL (e.g., `/transactions/45/edit`) without verifying ownership, allowing User B to alter User A's record by modifying the ID.  
We eliminate IDOR by always scoping lookups to the authenticated session user:
```python
transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first_or_404()
```
If an unauthorized user attempts to access another user's transaction ID, SQLAlchemy returns HTTP 404 (Not Found).

#### Q10: How does the application prevent SQL Injection?
**Answer:**  
All database interactions use SQLAlchemy ORM or parameterized queries. User input is separated from SQL syntax and delivered via prepared statement parameter placeholders (`%s`), preventing attacker-controlled input from breaking out of data literals into executable SQL commands.

#### Q11: What is CSRF and how did you prevent it?
**Answer:**  
Cross-Site Request Forgery (CSRF) occurs when a malicious website tricks an authenticated user's browser into submitting an unauthorized request to our application. We use **Flask-WTF** (`CSRFProtect`). Every HTML form includes `{{ form.hidden_tag() }}`, which injects a unique, session-bound cryptographic token that the server verifies upon submission.

#### Q12: How do you prevent Open Redirect vulnerabilities?
**Answer:**  
During login redirection (`next` query parameter), an attacker could try `/auth/login?next=https://evil-site.com`. In `app/routes/auth.py`, we parse the destination using `urllib.parse.urlsplit` and verify that `urlsplit(next_page).netloc == ""` (ensuring it is strictly a relative internal path) before issuing the redirect.

---

### SECTION 4: MACHINE LEARNING & MATHEMATICS

#### Q13: How does your AI expense forecasting model work?
**Answer:**  
We engineered an academically honest, multi-tiered forecasting strategy based on data availability:
1. **Tier 1 (Cold Start, $N < 3$ months):** Calculates a historical moving average with a transparent UI disclosure that data is preliminary.
2. **Tier 2 (Moderate Data, $3 \le N < 6$ months):** Fits a Scikit-Learn **Linear Trend Regression** model on the period index $t$.
3. **Tier 3 (Rich Data, $N \ge 6$ months):** Fits a **Regularized Ridge Regression** model using time index $t$, lag-1 feature $t-1$, and cyclical month sine/cosine transformations ($\sin(2\pi m / 12)$, $\cos(2\pi m / 12)$).

#### Q14: Why did you choose Mean Absolute Error (MAE) instead of Mean Squared Error (MSE)?
**Answer:**  
MSE squares error terms, making the metric unit squared currency ($\text{₹}^2$) and giving disproportionate weight to single one-off spikes (like an annual insurance payment). **Mean Absolute Error (MAE)** calculates $\frac{1}{n}\sum |y_i - \hat{y}_i|$, which is linear and expressed in exact currency units ($\pm ₹$). This provides a direct, intuitive measure of prediction accuracy for financial evaluators and users.

#### Q15: How did you prevent data leakage in your ML pipeline?
**Answer:**  
Standard k-fold random cross-validation shuffles data, allowing future observations to train past predictions (lookahead bias / data leakage). We enforce strict **temporal splitting**: the model trains on chronological past periods $t_1, \dots, t_{N-1}$ and tests strictly on the most recent holdout month $t_N$.

#### Q16: Explain the 50/30/20 rule implemented in your smart recommendations.
**Answer:**  
The 50/30/20 rule is an established personal finance guideline:
- **50% Needs:** Essential expenditures (Rent, Utilities, Groceries, Healthcare, Education).
- **30% Wants:** Discretionary expenditures (Dining out, Entertainment, Shopping, Travel).
- **20% Savings:** Net cash surplus and goal deposits.  
Our engine dynamically aggregates current month transactions into these categories. If discretionary spending exceeds 35%, it alerts the user and calculates the exact amount to trim to restore balance.

#### Q17: What formula calculates the required monthly savings for financial goals?
**Answer:**  
The amortization formula:
$$S_{\text{monthly}} = \frac{\text{Target Amount} - \text{Current Saved Amount}}{\text{Months Remaining Until Target Date}}$$
Where $\text{Months Remaining} = (\text{Year}_{\text{target}} - \text{Year}_{\text{today}}) \times 12 + (\text{Month}_{\text{target}} - \text{Month}_{\text{today}})$.

---

### SECTION 5: REPORTING & FULL-STACK IMPLEMENTATION

#### Q18: How does the application generate PDF reports without saving files to disk?
**Answer:**  
We use **ReportLab** writing to an in-memory binary stream (`io.BytesIO()`). The document story (paragraphs, metadata, executive summary table, transaction ledger) is compiled into memory and streamed directly as a Flask `Response` with mimetype `application/pdf` and `Content-Disposition: attachment`. This eliminates server disk writes, prevents race conditions, and leaves zero residual user data on disk.

#### Q19: How does the backend communicate with Chart.js on the frontend?
**Answer:**  
The service layer aggregates data from MySQL, structures it into dictionaries, and serializes it using `json.dumps(..., default=float)`. The Jinja2 template embeds the JSON safely into a `<script>` tag using the `|safe` filter (`{{ category_chart_json|safe }}`), where client-side JavaScript instantiates the Chart.js canvas object.

#### Q20: What happens if a database transaction fails halfway through?
**Answer:**  
Because MySQL uses the ACID-compliant InnoDB storage engine, multi-step operations (such as depositing a goal contribution and incrementing the goal's current total) are atomic. If an error occurs, our application's `500` error handler issues `db.session.rollback()`, ensuring the database rolls back to its prior consistent state without orphaned records.
