import os
from flask import Flask, render_template
from flask_login import current_user
from config import config
from models import db, login_manager, bcrypt, User, Doctor, Department, Patient
from controllers.auth_routes import auth_bp
from controllers.admin_routes import admin_bp
from controllers.doctor_routes import doctor_bp
from controllers.receptionist_routes import receptionist_bp
from controllers.nurse_routes import nurse_bp

def create_app(config_name=None):
    if not config_name:
        config_name = os.environ.get('FLASK_ENV', 'default')
    app = Flask(__name__,
        template_folder='views/templates',
        static_folder='views/static')
    app.config.from_object(config[config_name])
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(receptionist_bp)
    app.register_blueprint(nurse_bp)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('unauthorized.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.context_processor
    def inject_now():
        return {'now': __import__('datetime').datetime.now(__import__('datetime').timezone.utc)}

    @app.context_processor
    def inject_unread_notifications():
        if current_user.is_authenticated:
            from models import Notification
            count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            return {'unread_notifications': count}
        return {'unread_notifications': 0}

    return app

def init_database(app):
    with app.app_context():
        db.create_all()
        if not Department.query.first():
            dept = Department(name='General Medicine', description='General medical services',
                location='Ground Floor', phone='+1234567899')
            db.session.add(dept)
            db.session.commit()
            print("Database initialized with default department")

if __name__ == '__main__':
    app = create_app()
    init_database(app)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)
