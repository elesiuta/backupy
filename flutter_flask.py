from flask import Flask, request
from flask_cors import CORS
app = Flask(__name__)
CORS(app)


@app.route('/')
def hello():
    return "Hello World!"


@app.route('/name/<name>')
def hello_name(name):
    return "Hello {}!".format(name)


@app.route('/args/', methods=['POST'])
def hello_args():
    json = request.get_json()
    return "Hello {}".format(str(json))


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
