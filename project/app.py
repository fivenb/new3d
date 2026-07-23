from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from werkzeug.utils import secure_filename

import os
from pathlib import Path
from parse_bom import parse_excel

app = Flask(__name__)

UPLOAD_DIR = "uploads"
STATIC_DIR = "static"
def cleanup_old_files():

    files_to_remove = [
        "static/bom_tree_L4.json",
    ]

    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)

    for file in Path("uploads").glob("*"):
        if file.is_file():
            file.unlink()

cleanup_old_files()

@app.route("/")
def home():
    return render_template("upload.html")

@app.route("/upload", methods=["POST"])
def upload():

    file = request.files["excel"]

    filename = secure_filename(file.filename)

    excel_path = os.path.join(
        UPLOAD_DIR,
        filename
    )

    file.save(excel_path)

    parse_excel(
        excel_path,
        "static/bom_tree_L4.json"
    )

    return redirect("/viewer")

@app.route("/viewer")
def viewer():
    return render_template("bom_3d.html")

if __name__ == "__main__":
    app.run(debug=True)