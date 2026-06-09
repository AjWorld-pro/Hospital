from app import create_app, init_database

app = create_app()

if __name__ == '__main__':
    init_database(app)
    app.run()
