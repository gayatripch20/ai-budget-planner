from datetime import date, datetime
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_, and_, func
from app.extensions import db
from app.models.category import Category
from app.models.transaction import Transaction
from app.forms.transaction import TransactionForm, TransactionFilterForm

transactions_bp = Blueprint("transactions", __name__, url_prefix="/transactions")


def get_categories_for_user(trans_type: str):
    """Retrieve system default categories plus user custom categories for a given type."""
    return (
        Category.query.filter(
            Category.type == trans_type,
            or_(Category.user_id.is_(None), Category.user_id == current_user.id),
        )
        .order_by(Category.name.asc())
        .all()
    )


@transactions_bp.route("/<trans_type>")
@login_required
def list_transactions(trans_type: str):
    """
    List, search, and filter transactions for the authenticated user.
    trans_type can be 'income', 'expense', or 'all'.
    """
    if trans_type not in ["income", "expense", "all"]:
        abort(404)

    page = request.args.get("page", 1, type=int)
    per_page = 12

    # Base query restricted strictly to current authenticated user
    query = Transaction.query.filter(Transaction.user_id == current_user.id)

    if trans_type in ["income", "expense"]:
        query = query.filter(Transaction.transaction_type == trans_type)

    # Filtering logic
    filter_form = TransactionFilterForm(request.args, meta={"csrf": False})
    
    # Populate category dropdown for filter form
    categories = get_categories_for_user(trans_type if trans_type != "all" else "expense")
    if trans_type == "all":
        # Combine income and expense categories for the dropdown
        categories = (
            Category.query.filter(
                or_(Category.user_id.is_(None), Category.user_id == current_user.id)
            )
            .order_by(Category.type.asc(), Category.name.asc())
            .all()
        )
    
    filter_form.category_id.choices = [(0, "All Categories")] + [(c.id, f"{c.name} ({c.type.capitalize()})") for c in categories]

    # Apply filters
    selected_category = request.args.get("category_id", type=int)
    if selected_category and selected_category > 0:
        query = query.filter(Transaction.category_id == selected_category)

    payment_method = request.args.get("payment_method", type=str)
    if payment_method:
        query = query.filter(Transaction.payment_method == payment_method)

    start_date_str = request.args.get("start_date", type=str)
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            query = query.filter(Transaction.transaction_date >= start_date)
        except ValueError:
            pass

    end_date_str = request.args.get("end_date", type=str)
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            query = query.filter(Transaction.transaction_date <= end_date)
        except ValueError:
            pass

    search_kw = request.args.get("search", type=str)
    if search_kw:
        query = query.filter(Transaction.description.ilike(f"%{search_kw.strip()}%"))

    # Order newest transactions first
    query = query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())

    # Summary calculations for current month
    today = date.today()
    mtd_query = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == current_user.id,
        func.extract("year", Transaction.transaction_date) == today.year,
        func.extract("month", Transaction.transaction_date) == today.month,
    )
    if trans_type in ["income", "expense"]:
        mtd_total = mtd_query.filter(Transaction.transaction_type == trans_type).scalar()
    else:
        mtd_income = mtd_query.filter(Transaction.transaction_type == "income").scalar()
        mtd_expense = mtd_query.filter(Transaction.transaction_type == "expense").scalar()
        mtd_total = mtd_income - mtd_expense

    # Total of the filtered set
    filtered_total = query.with_entities(func.coalesce(func.sum(Transaction.amount), 0)).scalar()

    # Paginate results
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "transactions/transaction_list.html",
        transactions=pagination.items,
        pagination=pagination,
        trans_type=trans_type,
        filter_form=filter_form,
        mtd_total=Decimal(str(mtd_total or 0.00)),
        filtered_total=Decimal(str(filtered_total or 0.00)),
    )


@transactions_bp.route("/new/<trans_type>", methods=["GET", "POST"])
@login_required
def create_transaction(trans_type: str):
    """Create a new income or expense transaction."""
    if trans_type not in ["income", "expense"]:
        abort(404)

    form = TransactionForm()
    categories = get_categories_for_user(trans_type)
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        transaction = Transaction(
            user_id=current_user.id,
            category_id=form.category_id.data,
            transaction_type=trans_type,
            amount=form.amount.data,
            transaction_date=form.transaction_date.data,
            payment_method=form.payment_method.data,
            description=form.description.data.strip() if form.description.data else None,
        )
        db.session.add(transaction)
        db.session.commit()

        flash(
            f"{trans_type.capitalize()} of {current_user.currency}{form.amount.data} recorded successfully!",
            "success",
        )
        return redirect(url_for("transactions.list_transactions", trans_type=trans_type))

    return render_template(
        "transactions/transaction_form.html",
        form=form,
        trans_type=trans_type,
        action="Add",
    )


@transactions_bp.route("/<int:transaction_id>/edit", methods=["GET", "POST"])
@login_required
def edit_transaction(transaction_id: int):
    """Edit an existing transaction with strict user ownership validation."""
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first_or_404()

    form = TransactionForm(obj=transaction)
    categories = get_categories_for_user(transaction.transaction_type)
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        transaction.amount = form.amount.data
        transaction.category_id = form.category_id.data
        transaction.transaction_date = form.transaction_date.data
        transaction.payment_method = form.payment_method.data
        transaction.description = form.description.data.strip() if form.description.data else None

        db.session.commit()
        flash("Transaction updated successfully!", "success")
        return redirect(url_for("transactions.list_transactions", trans_type=transaction.transaction_type))

    return render_template(
        "transactions/transaction_form.html",
        form=form,
        trans_type=transaction.transaction_type,
        action="Edit",
        transaction=transaction,
    )


@transactions_bp.route("/<int:transaction_id>/delete", methods=["POST"])
@login_required
def delete_transaction(transaction_id: int):
    """Delete a transaction with ownership verification and CSRF protection."""
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first_or_404()
    trans_type = transaction.transaction_type

    db.session.delete(transaction)
    db.session.commit()

    flash("Transaction deleted successfully.", "info")
    return redirect(url_for("transactions.list_transactions", trans_type=trans_type))
