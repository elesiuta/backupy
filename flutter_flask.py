import os
import time

import psutil
from flask import Flask, request
from flask_cors import CORS
app = Flask(__name__)
CORS(app)


@app.route('/')
def hello():
    return "Hello World!"


@app.route('/terminate')
def terminate():
    os._exit(0)


@app.route('/watchparent')
def watchparent():
    # workaround since there appears to be no onDestroy in flutter
    # https://github.com/flutter/flutter/issues/21982
    self = psutil.Process(os.getpid())
    while True:
        if self.parent is not None:
            time.sleep(0.2)
            continue
        else:
            os._exit(0)


@app.route('/name/<name>')
def hello_name(name):
    return "Hello {}!".format(name)


@app.route('/args/', methods=['POST'])
def hello_args():
    json = request.get_json()
    return "Hello {}".format(str(json))


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
