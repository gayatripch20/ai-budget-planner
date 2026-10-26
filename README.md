# AI-Based Personal Budget Planning & Financial Goal System

An academic full-stack web application designed for personal finance tracking, monthly category budget limits, financial goal planning, historical expense analytics, and AI/ML-driven expense forecasting.

---

## Technology Stack
- **Backend:** Python 3, Flask, Flask-Login, Flask-WTF, Flask-SQLAlchemy, Flask-Migrate
- **Database:** MySQL 8.0 (InnoDB engine, 3NF normalized schema)
- **Machine Learning & Analytics:** Scikit-learn, Pandas, NumPy
- **Frontend:** HTML5, CSS3, JavaScript, Bootstrap 5, Chart.js
- **Reporting & Export:** ReportLab (PDF), CSV engine
- **Testing:** Pytest

---

## Project Structure
```text
ai_budget_planner/
├── app/
│   ├── models/            # SQLAlchemy Database Models (Users, Transactions, Budgets, Goals, etc.)
│   ├── routes/            # Blueprint Route Handlers (Auth, Dashboard, Transactions, Analytics, etc.)
│   ├── services/          # Business logic (Amortization, 50/30/20 Rule, Summary Aggregations)
│   ├── static/            # Custom CSS styles, JavaScript logic, and branding icons
│   ├── templates/         # Jinja2 Modular HTML templates with Bootstrap 5
│   └── utils/             # Helper decorators, date formatters, and flash utilities
├── ml/
│   ├── preprocessing.py   # Historical transaction aggregations & time-series feature engineering
│   ├── forecasting.py     # Linear/Ridge regression model + Cold-start fallback engine
│   └── evaluation.py      # MAE, Baseline comparison, and residual analysis
├── tests/                 # Automated test suite with Pytest
├── migrations/            # Alembic database migration scripts
├── config.py              # Environment configuration & database connection factory
├── run.py                 # Application entry point
├── requirements.txt       # Frozen Python dependencies
├── .env.example           # Environment variables template
├── .gitignore             # Standard Git ignore rules
└── README.md              # Project documentation
```

---

## Environment Setup & Installation (Windows)

1. Open PowerShell or Command Prompt in the project directory:
   ```powershell
   cd C:\Users\chokh\.gemini\antigravity\scratch\ai_budget_planner
   ```

2. Activate the Python virtual environment:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   *(If script execution is restricted on Windows, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

3. Verify dependencies:
   ```powershell
   pytest tests/test_environment.py
   ```

4. Configure the `.env` file:
   - Copy `.env.example` to `.env`
   - Set your MySQL root password and preferred settings.
