import os
import torch
import shutil
import cv2
import mimetypes
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from ultralytics import YOLO
import random
from sqlalchemy import func, text
from sklearn.model_selection import train_test_split
import pymysql
import logging
import traceback
import threading
import time
import requests

load_dotenv()
app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['DEBUG'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

secret_key = os.urandom(24)
app.secret_key = secret_key

db = SQLAlchemy(app)

SERVICE_DISCOVERY_BACKEND = os.getenv('SERVICE_DISCOVERY_BACKEND', 'redis')

if SERVICE_DISCOVERY_BACKEND == 'redis':
    from redis_discovery import redis_bp as discovery_bp
    logger.info("Using Redis for service discovery")
else:
    # Создаем mock blueprint
    from flask import Blueprint
    discovery_bp = Blueprint('discovery', __name__, url_prefix='/discovery')
        
    @discovery_bp.route('/register', methods=['POST'])
    def register():
         return jsonify({"status": "mock", "message": "Service discovery disabled"})

# Регистрируем blueprint
app.register_blueprint(discovery_bp)

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    photo = db.Column(db.String(255), nullable=False) 
    processed_photo = db.Column(db.String(255), nullable=True)
    txt = db.Column(db.String(255), nullable=True)
    is_discovered = db.Column(db.Boolean, nullable=False, default=0) 
    photo_date = db.Column(db.DateTime, nullable=False)
    modul = db.Column(db.Boolean, nullable=False)

class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    dataset = db.Column(db.String(255), nullable=False)

class Model(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    model = db.Column(db.String(255), nullable=False)

with app.app_context():
    db.create_all()


def get_video_filename(video_path):
    return os.path.basename(video_path)

def extract_frames(video_path, output_folder, frame_rate=10, db_session=None):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    video_capture = cv2.VideoCapture(video_path)
    video_filename = get_video_filename(video_path)
    
    if not video_capture.isOpened():
        print("Ошибка: Не удалось открыть видео.")
        return

    fps = video_capture.get(cv2.CAP_PROP_FPS)
    frame_interval = int(fps * frame_rate) # для кадра надо делить
    current_frame = 0
    frame_count = 0

    while True:
        ret, frame = video_capture.read()
        
        if not ret:
            break

        if current_frame % frame_interval == 0:
            frame_filename = f"{video_filename}_{frame_count:04d}.jpg"
            frame_path = os.path.join(output_folder, frame_filename)
            cv2.imwrite(frame_path, frame)
            relative_path = os.path.relpath(frame_path, start=os.path.join(os.path.dirname(__file__), "static"))
            relative_path = relative_path.replace("\\", "/")
            file_creation_date = datetime.fromtimestamp(os.path.getctime(video_path))
            new_photo = Photo(photo=relative_path, is_discovered=0, photo_date=file_creation_date)
            db_session.add(new_photo)
            frame_count += 1
        
        current_frame += 1

    video_capture.release()
    print(f"Извлечено {frame_count} кадров в папку '{output_folder}'.")

@app.route('/')
def index():
    try:
        photos = Photo.query.filter(
            Photo.modul == 0,
            Photo.processed_photo.isnot(None)
        ).order_by(Photo.id.desc()).all()
        
        print(f"Displaying {len(photos)} processed photos")
        
        models = Model.query.all()
        return render_template('index.html', photos=photos, models=models)
    except Exception as e:
        logger.error(f"Error in index: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Error: {str(e)}", 500

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return "No file part", 400
    
    try:
        files = request.files.getlist('files')
        
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(backend_dir)
        static_dir = os.path.join(project_root, 'frontend', 'static')
        
        base_images_dir = os.path.join(static_dir, "base_images")
        os.makedirs(base_images_dir, exist_ok=True)
        
        saved_count = 0
        
        for file in files:
            if file.filename == '':
                continue
            
            mime_type, _ = mimetypes.guess_type(file.filename)
            if mime_type and mime_type.startswith('video/'):
                video_path = os.path.join(base_images_dir, file.filename)
                file.save(video_path)
                # Для видео создаем output_folder в static
                output_folder = os.path.join(static_dir, "video_frames")
                extract_frames(video_path, output_folder, frame_rate=10, db_session=db.session)
            else:
                filename = file.filename
                photo_path = os.path.join(base_images_dir, filename)
                file.save(photo_path)
                
                relative_path = os.path.relpath(photo_path, static_dir)
                relative_path = relative_path.replace("\\", "/")
                
                file_creation_date = datetime.fromtimestamp(os.path.getctime(photo_path))
                new_photo = Photo(
                    photo=relative_path, 
                    is_discovered=0, 
                    photo_date=file_creation_date, 
                    modul=0,
                    processed_photo=None  # Явно указываем, что не обработано
                )
                db.session.add(new_photo)
                saved_count += 1
        
        db.session.commit()
        print(f"Saved {saved_count} files to database")
        
        # Запускаем обработку
        print("Starting YOLO predictions...")
        run_yolo_predictions()
        
        return redirect(url_for('index'))
    
    except Exception as e:
        logger.error(f"Error in upload: {str(e)}")
        logger.error(traceback.format_exc())
        db.session.rollback()
        return f"Error: {str(e)}", 500

def run_yolo_predictions():
    try:
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(backend_dir)
        static_dir = os.path.join(project_root, 'frontend', 'static')
        
        model_path = os.path.join(static_dir, "best.pt")
        
        if not os.path.exists(model_path):
            print(f"Model not found at {model_path}")
            return
        
        model = YOLO(model_path)
        
        # Берем фото без processed_photo (новые или необработанные)
        photos = Photo.query.filter(
            Photo.modul == 0,
            Photo.processed_photo.is_(None)  # Только необработанные
        ).all()
        
        if not photos:
            print("No photos to process")
            return
        
        print(f"Processing {len(photos)} photos...")
        
        # Создаем временную папку для предсказаний
        temp_predict_folder = os.path.join(backend_dir, "temp_predict")
        os.makedirs(temp_predict_folder, exist_ok=True)
        
        # Копируем фото во временную папку
        for photo in photos:
            source_path = os.path.join(static_dir, photo.photo)
            if os.path.exists(source_path):
                dest_path = os.path.join(temp_predict_folder, os.path.basename(photo.photo))
                shutil.copy2(source_path, dest_path)
                print(f"Copied: {os.path.basename(photo.photo)}")
        
        # Выполняем предсказание
        results = model.predict(temp_predict_folder, save=True)
        
        # Папка с результатами YOLO
        yolo_output_folder = os.path.join(backend_dir, "runs", "detect", "predict")
        
        # Папка для сохранения обработанных изображений
        processed_images_dir = os.path.join(static_dir, "processed_images")
        os.makedirs(processed_images_dir, exist_ok=True)
        
        # Обрабатываем результаты
        for photo in photos:
            # Ищем результат для текущего фото
            result_for_photo = None
            for result in results:
                if os.path.basename(result.path) == os.path.basename(photo.photo):
                    result_for_photo = result
                    break
            
            if result_for_photo:
                # Проверяем наличие повреждений
                damage_detected = False
                if result_for_photo.boxes is not None and len(result_for_photo.boxes) > 0:
                    for box in result_for_photo.boxes:
                        class_id = int(box.cls)
                        label = result_for_photo.names[class_id]
                        print(f"Detected: {label} in {photo.photo}")
                        if label == 'Empty':  # Ваша метка для пустых/поврежденных мест
                            damage_detected = True
                            break
                
                if damage_detected:
                    photo.is_discovered = 1
                    
                    # Копируем обработанное изображение
                    yolo_output_path = os.path.join(yolo_output_folder, os.path.basename(photo.photo))
                    if os.path.exists(yolo_output_path):
                        dest_path = os.path.join(processed_images_dir, os.path.basename(photo.photo))
                        shutil.copy2(yolo_output_path, dest_path)
                        
                        # Сохраняем относительный путь
                        relative_processed = os.path.relpath(dest_path, static_dir)
                        relative_processed = relative_processed.replace("\\", "/")
                        photo.processed_photo = relative_processed
                        print(f"Saved processed image: {relative_processed}")
                    else:
                        print(f"YOLO output not found: {yolo_output_path}")
                else:
                    photo.is_discovered = 0
                    # Создаем запись что фото обработано, но повреждений нет
                    # Можно скопировать оригинал как processed_photo или оставить None
                    print(f"No damage detected in {photo.photo}")
                    
                    # Опционально: копируем оригинал как processed_photo
                    source_path = os.path.join(static_dir, photo.photo)
                    if os.path.exists(source_path):
                        dest_path = os.path.join(processed_images_dir, f"no_damage_{os.path.basename(photo.photo)}")
                        shutil.copy2(source_path, dest_path)
                        relative_processed = os.path.relpath(dest_path, static_dir)
                        relative_processed = relative_processed.replace("\\", "/")
                        photo.processed_photo = relative_processed
            else:
                print(f"No result found for {photo.photo}")
        
        db.session.commit()
        
        # Очищаем временные папки
        if os.path.exists(temp_predict_folder):
            shutil.rmtree(temp_predict_folder)
        if os.path.exists(os.path.join(backend_dir, "runs")):
            shutil.rmtree(os.path.join(backend_dir, "runs"))
            
        print("YOLO predictions completed successfully")
        
    except Exception as e:
        print(f"Error in run_yolo_predictions: {str(e)}")
        print(traceback.format_exc())
        db.session.rollback()


@app.route('/model')
def model():
    photos = Photo.query.filter_by(modul=1).order_by(Photo.id.desc()).all()
    filenames = [os.path.basename(photo.photo) for photo in photos]
    non_empty_count = db.session.query(func.count(Photo.txt)).filter(Photo.txt.isnot(None), Photo.txt != '').scalar() 

    datasets = Dataset.query.all()

    return render_template('model.html', photos=photos, filenames=filenames, non_empty_count=non_empty_count, datasets=datasets)

@app.route('/upload_model_files', methods=['POST'])
def upload_model_files():
    if 'files' not in request.files:
        return "No file part", 400
    
    files = request.files.getlist('files')
    images_dir = os.path.join(os.path.dirname(__file__), "static", "model_images")
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)

    new_entries = []
    for file in files:
        if file.filename == '':
            return "No selected file", 400
        
        filename = file.filename
        file_extension = os.path.splitext(filename)[1].lower()
        file_path = os.path.join(images_dir, filename)
        
        try:
            file.save(file_path)
            print(f"Файл сохранен: {file_path}")
        except Exception as e:
            print(f"Ошибка при сохранении файла {filename}: {e}")
            return "Error saving file", 500

    for file in files:
        filename = file.filename
        file_extension = os.path.splitext(filename)[1].lower()
        relative_image_path = os.path.relpath(os.path.join(images_dir, filename), start=os.path.join(os.path.dirname(__file__), "static"))
        relative_image_path = relative_image_path.replace("\\", "/")
        
        txt_path = None
        
        if file_extension == '.txt':
            image_filename = 'model_images/' + os.path.splitext(filename)[0] + '.jpg'
            existing_entry = Photo.query.filter_by(photo=image_filename).first()
            
            if existing_entry:
                existing_entry.txt = relative_image_path
                print(f"Обновлено поле txt для {image_filename}")
            else:
                print(f"Запись для {image_filename} не найдена в базе данных.")
        else:
            txt_filename = os.path.splitext(filename)[0] + '.txt'
            txt_file_path = os.path.join(images_dir, txt_filename)
            
            if os.path.exists(txt_file_path):
                txt_path = os.path.relpath(txt_file_path, start=os.path.join(os.path.dirname(__file__), "static"))
                txt_path = txt_path.replace("\\", "/")
                print(f"Текстовый файл найден: {txt_path}")
            else:
                print(f"Текстовый файл не найден: {txt_file_path}")

            new_entries.append(Photo(photo=relative_image_path, txt=txt_path, photo_date=datetime.now(), modul=1))

    try:
        db.session.bulk_save_objects(new_entries)
        db.session.commit()
        print("Записи успешно добавлены в базу данных.")
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при сохранении в базу данных: {e}")
        return "Error saving to database", 500

    return redirect(url_for('model'))

@app.route('/copy_photos', methods=['POST'])
def copy_photos():
    num_photos = request.form.get('num_photos', type=int)
    dataset_name = request.form.get('dataset_name') 
    destination_folder = os.path.join(os.path.dirname(__file__), 'datasets')
    train_size = request.form.get('train_size', type=float)
    val_size = request.form.get('val_size', type=float)

    if dataset_name is None:
        return jsonify({"error": "Необходимо указать название датасета."}), 400

    if destination_folder is None:
        return jsonify({"error": "Необходимо указать путь к папке назначения."}), 400

    if train_size + val_size != 1.0:
        return jsonify({"error": "Сумма train_size и val_size должна быть равна 1."}), 400

    yolo_folder = os.path.join(destination_folder, dataset_name) 
    dataset_folder = os.path.join(yolo_folder, 'dataset')

    if os.path.exists(yolo_folder):
        return jsonify({"exists": True, "message": "Папка с таким именем уже существует. Продолжить?"}), 409

    try:
        os.makedirs(yolo_folder, exist_ok=True)
        os.makedirs(dataset_folder, exist_ok=True)
        os.makedirs(os.path.join(yolo_folder, 'train'), exist_ok=True)
        os.makedirs(os.path.join(yolo_folder, 'val'), exist_ok=True)
    except Exception as e:
        return jsonify({"error": f"Не удалось создать папку: {str(e)}"}), 500

    photos = Photo.query.filter(Photo.txt.isnot(None), Photo.modul == 1).all()
    print(f"Количество фотографий с текстом в базе данных: {len(photos)}")
    
    if not photos:
        return jsonify({"error": "Нет фотографий с текстом в базе данных."}), 400

    if num_photos > len(photos):
        return jsonify({"error": "Недостаточно фотографий с текстом в базе данных."}), 400

    selected_photos = random.sample(photos, num_photos)

    for photo in selected_photos:
        photo_path = os.path.join('static', photo.photo)
        print(f"Исходный путь к изображению: {photo_path}")
        
        destination_photo_path = os.path.join(dataset_folder, os.path.basename(photo.photo))  # Сохраняем в dataset
        print(f"Путь к копируемому изображению: {destination_photo_path}")
        
        try:
            if os.path.exists(photo_path):
                shutil.copy(photo_path, destination_photo_path)
            else:
                print(f"Файл изображения не найден: {photo_path}")
                return jsonify({"error": f"Файл изображения не найден: {photo_path}"}), 404
        except Exception as e:
            print(f"Ошибка при копировании файла {photo.photo}: {str(e)}")
            return jsonify({"error": f"Ошибка при копировании файла {photo.photo}: {str(e)}"}), 500

        if photo.txt:
            txt_path = os.path.join('static', photo.txt)
            print(f"Исходный путь к текстовому файлу: {txt_path}")
            
            destination_txt_path = os.path.join(dataset_folder, os.path.basename(photo.txt))  # Сохраняем в dataset
            print(f"Путь к копируемому текстовому файлу: {destination_txt_path}")
            
            try:
                if os.path.exists(txt_path):
                    shutil.copy(txt_path, destination_txt_path)
                else:
                    print(f"Текстовый файл не найден: {txt_path}")
                    return jsonify({"error": f"Текстовый файл не найден: {txt_path}"}), 404
            except Exception as e:
                print(f"Ошибка при копировании текстового файла {photo.txt}: {str(e)}")
                return jsonify({"error": f"Ошибка при копировании текстового файла {photo.txt}: {str(e)}"}), 500

    split_and_save_dataset(dataset_folder, yolo_folder, test_size=val_size)
    
    new_dataset = Dataset(dataset=yolo_folder)
    try:
        db.session.add(new_dataset)
        db.session.commit()
    except Exception as e:
        db.session.rollback() 
        return jsonify({"error": f"Не удалось сохранить датасет в базе данных: {str(e)}"}), 500

    return redirect(url_for('model')) 

def split_and_save_dataset(source_folder, destination_folder, test_size):
    all_files = os.listdir(source_folder)
    
    images = [f for f in all_files if f.endswith(('.jpg', '.jpeg', '.png'))]
    texts = [f for f in all_files if f.endswith('.txt')]

    images_with_texts = [img for img in images if os.path.splitext(img)[0] + '.txt' in texts]
    train_files, val_files = train_test_split(images_with_texts, test_size=test_size, random_state=42)

    train_folder = os.path.join(destination_folder, 'train')
    val_folder = os.path.join(destination_folder, 'val')

    os.makedirs(train_folder, exist_ok=True)
    os.makedirs(val_folder, exist_ok=True)

    for file in train_files:
        shutil.copy(os.path.join(source_folder, file), os.path.join(train_folder, file))
        txt_file = os.path.splitext(file)[0] + '.txt'
        if txt_file in texts:
            shutil.copy(os.path.join(source_folder, txt_file), os.path.join(train_folder, txt_file))

    for file in val_files:
        shutil.copy(os.path.join(source_folder, file), os.path.join(val_folder, file))
        txt_file = os.path.splitext(file)[0] + '.txt'
        if txt_file in texts:
            shutil.copy(os.path.join(source_folder, txt_file), os.path.join(val_folder, txt_file))

    print(f"Количество файлов в train: {len(train_files)}")
    print(f"Количество файлов в val: {len(val_files)}")

@app.route('/create_class', methods=['POST'])
def create_class():
    selected_dataset = request.form.get('selected_dataset')
    class_name = request.form.get('class_name')

    print(f"Выбранный датасет: {selected_dataset}")
    print(f"Имя класса: {class_name}") 

    if selected_dataset and class_name:
        dataset_folder = selected_dataset 
        print(f"Папка датасета: {dataset_folder}")

        classes_file_path = os.path.join(dataset_folder, 'classes.txt')
        data_yaml_path = os.path.join(dataset_folder, 'data.yaml')

        try:
            with open(classes_file_path, 'a') as f:
                f.write(class_name + '\n')
            print(f"Имя класса '{class_name}' добавлено в файл '{classes_file_path}'")
        except Exception as e:
            print(f"Ошибка при записи в {classes_file_path}: {e}")

        try:
            with open(classes_file_path, 'r') as f:
                class_names = [line.strip() for line in f.readlines()]
            print(f"Имена классов: {class_names}")
        except Exception as e:
            print(f"Ошибка при чтении из {classes_file_path}: {e}")
            class_names = []

        num_classes = len(class_names)

        try:
            with open(data_yaml_path, 'w') as f:
                f.write(f"train: ./train\n")
                f.write(f"val: ./val\n")
                f.write(f"nc: {num_classes}\n")
                f.write(f"names: {class_names}\n")
            print(f"Файл {data_yaml_path} успешно создан.")
        except Exception as e:
            print(f"Ошибка при записи в {data_yaml_path}: {e}")
    else:
        print("Не удалось получить выбранный датасет или имя класса.")
    
    return redirect(url_for('model')) 

@app.route('/create_train_script', methods=['POST'])
def create_train_script():
    try:
        imgsz = int(request.form['imgsz'])
        epochs = int(request.form['epochs'])
        batch = int(request.form['batch'])
        save_period = int(request.form['save_period'])
        selected_dataset = request.form['selected_dataset']

        if not selected_dataset.endswith(os.path.sep):
            selected_dataset += os.path.sep

        script_path = os.path.join(selected_dataset, 'train.py')
        path = selected_dataset.replace("\\", "\\\\")
        
        script_content = f"""import torch
import os
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"

from ultralytics import YOLO

if __name__ == "__main__":
    model = YOLO('yolo11n.pt')
    results = model.train(
        data='{os.path.join(path, 'data.yaml')}',
        imgsz={imgsz},
        epochs={epochs},
        batch={batch},
        save_period={save_period}
    )
"""

        with open(script_path, 'w') as f:
            f.write(script_content)

        print('Файл train.py успешно создан!', 'success')
    except Exception as e:
        print(f'Ошибка при создании файла: {e}', 'error')

    return redirect(url_for('model'))

@app.route('/train', methods=['POST'])
def train():
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    try:
        imgsz = int(request.form['imgsz'])
        epochs = int(request.form['epochs'])
        batch = int(request.form['batch'])
        save_period = int(request.form['save_period'])
        selected_dataset = request.form['selected_dataset']
        model_name = request.form['model_name']

        if not selected_dataset.endswith(os.path.sep):
            selected_dataset += os.path.sep

        path = os.path.normpath(selected_dataset)
        data_yaml_path = os.path.join(path, 'data.yaml')

        if not os.path.exists(data_yaml_path):
            print(f'Ошибка: файл не найден по пути {data_yaml_path}')
            return redirect(url_for('model'))
        
        results_dir = os.path.join(path, 'runs')

        model = YOLO('yolo11n.pt')
        results = model.train(
            data=data_yaml_path,
            imgsz=imgsz,
            epochs=epochs,
            batch=batch,
            save_period=save_period,
            name=results_dir 
        )
        print('Обучение завершено успешно!', 'success')

        model = os.path.join(results_dir, 'weights', 'best.pt')
        destination_path = os.path.join('static', 'models', f"{model_name}") 
        destination_path = destination_path.replace("\\", "/")
        if not os.path.exists(destination_path):
            os.makedirs(destination_path)
        shutil.copy(model, destination_path)

        new_model = Model(model=destination_path)
        try:
            db.session.add(new_model)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Не удалось сохранить модель в базе данных: {str(e)}"}), 500
        
    except Exception as e:
        print(f'Ошибка при обучении: {e}', 'error')
    
    return redirect(url_for('model'))


@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Проверка БД
        db.session.execute(text("SELECT 1"))
        
        # Проверка Redis если используется
        redis_status = "not_configured"
        if SERVICE_DISCOVERY_BACKEND == 'redis':
            try:
                import redis
                r = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'redis'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    decode_responses=True
                )
                r.ping()
                redis_status = "connected"
            except Exception as e:
                redis_status = f"error: {str(e)}"
        
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "service_discovery": SERVICE_DISCOVERY_BACKEND,
            "redis": redis_status,
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

def register_current_service():
    """Автоматическая регистрация текущего сервиса"""
    service_id = f"flask-backend-{os.getenv('HOSTNAME', 'default')}"
    service_address = "app"  # Имя сервиса в Docker сети
    service_port = 5000
    
    tags = ["api", "v1", "web", "analytics"]
    
    registration_data = {
        "id": service_id,
        "name": "analytics-service",
        "address": service_address,
        "port": service_port,
        "tags": tags,
        "metadata": {
            "version": "1.0.0",
            "framework": "flask",
            "python_version": "3.11"
        }
    }
    
    try:
        # Ждем запуска приложения
        time.sleep(3)
        
        # Регистрируемся через внутренний эндпоинт
        response = requests.post(
            "http://localhost:5000/discovery/register",
            json=registration_data,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully registered with {SERVICE_DISCOVERY_BACKEND}: {service_id}")
        else:
            logger.error(f"Failed to register: {response.text}")
            
    except Exception as e:
        logger.error(f"Error during service registration: {str(e)}")

# ... (остальной код app.py без изменений) ...

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Регистрируем сервис в отдельном потоке
        registration_thread = threading.Thread(target=register_current_service, daemon=True)
        registration_thread.start()
    
    app.run(debug=True, host='0.0.0.0', port=5000)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)