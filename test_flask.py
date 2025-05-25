from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello, World!"

@app.route('/search', methods=['POST'])
def search():
    return {"message": "Test search endpoint"}, 200

if __name__ == '__main__':
    app.run(debug=True, port=5001)