from flask import Flask, request, render_template
import requests, os, werkzeug, json, time
from PIL import Image, ImageDraw
from pymongo import MongoClient
from time import clock
from bson.objectid import ObjectId

app = Flask(__name__)
UPLOAD_FOLDER='/root/image'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
basedir = os.path.abspath(os.path.dirname(__file__))
ALLOWED_EXTENSIONS = set(['png','jpg','JPG','PNG'])

client = MongoClient('127.0.0.1')
db = client.get_database('emotion')
collection = db.get_collection('recognizer')

result_json = """
{
    "code": %d,
    "msg": "%s",
    "face": %s,
    "time": %f
}
"""
ok_code = 0
size_code = 429
error_code = 430

# 用于判断文件后缀
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1] in ALLOWED_EXTENSIONS

@app.route('/share/<document_id>')
def share(document_id):
    document = collection.find_one({"_id":ObjectId(document_id)})
    return render_template('static/comment.html', path = document['raw']) if not document else 'hello'

@app.route('/recognize', methods=['POST'])
def recognize():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = time.strftime('%Y-%m-%d_%H:%M:%S_',time.localtime(time.time())) + werkzeug.secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            url = 'https://westus.api.cognitive.microsoft.com/face/v1.0/detect'
            headers = {
                # Request headers
                'Content-Type': 'application/octet-stream',
                'Ocp-Apim-Subscription-Key': '4a73eb2727a7496eb0d9e264d782f6ad',
            }
            params = {
                'returnFaceAttributes': 'age,gender,emotion'
            }
            src = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            start_time = clock()
            r = requests.post(url, headers = headers, data=open(src, 'rb'), params=params)
            end_time = clock()

            if r.status_code == 200:
                json_dict = json.loads(r.text)
                rectangle = json_dict[0]['faceRectangle']
                f = Image.open(src)
                paint = ImageDraw.Draw(f)
                paint.rectangle([(rectangle['left'], rectangle['top']), (rectangle['left'] + rectangle['width'], rectangle['top'] + rectangle['height'])])
                des = os.path.join(app.config['UPLOAD_FOLDER'], 'res_' + filename)
                f.save(des, 'JPEG')
                row_id = collection.insert({
                    'raw': src,
                    'res': des,
                    'time': ((end_time - start_time)),
                    'happy': 0,
                    'sad': 0,
                    "surprise": 0,
                    "hate": 0,
                    "angry": 0,
                    "fear": 0
                })
                return result_json % (ok_code, row_id, json.dumps((json_dict[0])), float(end_time - start_time))
            elif r.status_code == 429:
                # size too big
                return result_json % (size_code, '', '', -1)
            else:
                # other error
                return result_json % (error_code, '', '', -1)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

