import os
import subprocess
import sys

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


@app.route('/name/<name>')
def hello_name(name):
    return "Hello {}!".format(name)


@app.route('/args/', methods=['POST'])
def hello_args():
    json = request.get_json()
    return "Hello {}".format(str(json))


if __name__ == '__main__':
    # workaround since there appears to be no onDestroy in flutter
    # https://github.com/flutter/flutter/issues/21982
    subprocess.Popen([sys.executable, "flutter_watcher.py", str(os.getpid()), str(os.getppid())])
    app.run(host='127.0.0.1', port=5000)
