# coding=utf-8
from flask import Blueprint, get_flashed_messages, request, flash, render_template, url_for, redirect, abort

from utils.models import User, UserForm
from www.utils import acquire_admin
from . import app

__author__ = 'zephor'


admin = Blueprint('admin', __name__, url_prefix='/admin/')


@admin.route('user/list')
def user_list():
    context = {
        'count': User.objects.count(),
        'flashes': get_flashed_messages()
    }
    page = int(request.args.get('page', 1))
    context.update({'users': User.objects.order_by('role', 'username').paginate(page=page, per_page=32)})
    return render_template('user/list.html', **context)


@admin.route('user/add', methods=['GET', 'POST'])
@admin.route('user/edit/<user_id>', methods=['GET', 'POST'])
@acquire_admin
def user_add(user_id=None):
    user = None
    is_add = True
    if user_id is not None:
        is_add = False
        user = User.objects.get_or_404(id=user_id)

    user_form = UserForm(request.form, obj=user)
    if request.method == 'POST' and user_form.validate():
            if user_id is None:
                # add
                user = user_form.save()
            else:
                # update
                user_form.populate_obj(user)
                user.save()
            flash('user %s %s successfully' % (user.username, ('updated', 'added')[is_add]))
            return redirect(url_for('admin.user_list'))

    return render_template('user/add.html', form=user_form, is_add=is_add)


@admin.route('user/delete', methods=['POST'])
@acquire_admin
def user_del():
    user_id = request.form.get('user_id')
    if user_id is None:
        abort(404)
    user = User.objects.get_or_404(id=user_id)
    user.delete()


app.register_blueprint(admin)
