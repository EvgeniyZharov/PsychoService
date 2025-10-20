from app import create_app

app = create_app()
# app.config['DEBUG'] = True
# app.config['PROPAGATE_EXCEPTIONS'] = True

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8020, debug=True)
    # app.run(host='0.0.0.0', port=8020, debug=False)
    # app.run(port=80, debug=True)
