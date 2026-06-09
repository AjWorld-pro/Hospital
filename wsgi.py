from app import create_app, init_database

app = create_app()
init_database(app)

if __name__ == '__main__':
    app.run()
