from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from extensions import db  # Import db from extensions.py
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import base64
import uuid
import cv2
import numpy as np
import tensorflow as tf
# from flask_cors import CORS
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input
from tensorflow.keras.utils import img_to_array, load_img

import traceback
import json
from sqlalchemy.sql import func
from models import Consultation, Progress
# Flask setup
app = Flask(__name__)
# CORS(app)
app.secret_key = 'your_secret_key'  # Change this to a secure secret key in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload


# Initialize db with the app
db.init_app(app)
from models import Consultation,Progress
model = MobileNetV2(weights="imagenet")  

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        """Hash the password and set it to the password_hash field"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the hashed password"""
        return check_password_hash(self.password_hash, password)
    
    progress = db.relationship('Progress', backref='user', lazy='dynamic')

def analyze_skin_image(image_path):
    try:
        # Load and preprocess the image
        img = load_img(image_path, target_size=(224, 224))
        img_array = img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)

        # Get predictions from MobileNetV2
        predictions = model.predict(img_array)
        
        # Mock detection scores for specific conditions
        # In a real implementation, you'd use a specialized model for each condition
        mock_scores = {
            "acne": np.random.uniform(0.3, 0.8),
            "eczema": np.random.uniform(0.2, 0.7),
            "psoriasis": np.random.uniform(0.1, 0.6),
            "hyperpigmentation": np.random.uniform(0.2, 0.8),
            "wrinkles": np.random.uniform(0.3, 0.7),
            "eyebags": np.random.uniform(0.2, 0.6)
        }

        # Determine skin type based on image analysis
        skin_types = ["Oily", "Dry", "Combination", "Normal", "Sensitive"]
        skin_type = np.random.choice(skin_types, p=[0.25, 0.25, 0.2, 0.2, 0.1])

        # Generate severity levels
        def get_severity(score):
            if score < 0.3: return "Mild"
            elif score < 0.6: return "Moderate"
            else: return "Severe"

        # Structure the analysis results
        skin_analysis = {
            "skin_type": {
                "type": skin_type,
                "confidence": float(np.random.uniform(0.7, 0.9))
            },
            "conditions": {
                condition: {
                    "detected": score > 0.3,
                    "severity": get_severity(score),
                    "confidence": float(score),
                    "affected_areas": ["T-zone", "Cheeks", "Forehead"] if score > 0.3 else []
                } for condition, score in mock_scores.items()
            },
            "recommendations": {
                "skincare_routine": {
                    "morning": [
                        "Gentle cleanser",
                        "Toner",
                        "Vitamin C serum",
                        "Moisturizer",
                        "Sunscreen (SPF 30+)"
                    ],
                    "evening": [
                        "Oil-based cleanser",
                        "Water-based cleanser",
                        "Treatment serum",
                        "Moisturizer",
                        "Night cream"
                    ]
                },
                "products": {
                    "cleanser": get_product_recommendation(skin_type, "cleanser"),
                    "moisturizer": get_product_recommendation(skin_type, "moisturizer"),
                    "treatment": get_product_recommendation(skin_type, "treatment"),
                    "sunscreen": get_product_recommendation(skin_type, "sunscreen")
                },
                "lifestyle": [
                    "Stay hydrated - drink at least 8 glasses of water daily",
                    "Get 7-8 hours of sleep",
                    "Protect skin from sun exposure",
                    "Maintain a balanced diet rich in antioxidants"
                ]
            }
        }

        return skin_analysis

    except Exception as e:
        print(f"Error in analyze_skin_image: {str(e)}")
        return {
            "error": str(e),
            "skin_type": {"type": "Unknown", "confidence": 0},
            "conditions": {},
            "recommendations": {}
        }

def get_product_recommendation(skin_type, product_type):
    """Helper function to get product recommendations based on skin type"""
    recommendations = {
        "Oily": {
            "cleanser": "Salicylic acid cleanser",
            "moisturizer": "Oil-free gel moisturizer",
            "treatment": "Niacinamide serum",
            "sunscreen": "Light, oil-free sunscreen"
        },
        "Dry": {
            "cleanser": "Cream-based gentle cleanser",
            "moisturizer": "Rich, hydrating cream",
            "treatment": "Hyaluronic acid serum",
            "sunscreen": "Moisturizing sunscreen"
        },
        "Combination": {
            "cleanser": "Balanced pH cleanser",
            "moisturizer": "Light-weight lotion",
            "treatment": "BHA/AHA toner",
            "sunscreen": "Dual-action sunscreen"
        },
        "Normal": {
            "cleanser": "Mild foam cleanser",
            "moisturizer": "Balance moisturizer",
            "treatment": "Vitamin C serum",
            "sunscreen": "Daily protection sunscreen"
        },
        "Sensitive": {
            "cleanser": "Fragrance-free gentle cleanser",
            "moisturizer": "Calming moisturizer",
            "treatment": "Centella asiatica serum",
            "sunscreen": "Mineral sunscreen"
        }
    }
    return recommendations.get(skin_type, {}).get(product_type, "Generic recommendation")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):  # Check hashed password
            session['user_id'] = user.id
            session['user_name'] = user.name
            return redirect(url_for('index'))
        
        return render_template('signin.html', error="Invalid email or password")
    
    return render_template('signin.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        print(request.form)  # Print the form data for debugging
        
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Check if the email already exists in the database
        if User.query.filter_by(email=email).first():
            return render_template('signup.html', error="Email already exists")
        
        # Check if passwords match
        if password != confirm_password:
            return render_template('signup.html', error="Passwords do not match")
        
        # Create a new user with hashed password for security
        new_user = User(name=name, email=email)
        new_user.set_password(password)  # Hash the password before saving
        db.session.add(new_user)
        db.session.commit()
        
        # Log the user in automatically after successful registration
        session['user_id'] = new_user.id
        session['user_name'] = new_user.name
        
        return redirect(url_for('index'))  # Redirect to the homepage

    return render_template('signup.html')

@app.route('/signout')
def signout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/book-consultation', methods=['GET', 'POST'])
def book_consultation():
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        date = request.form['date']
        message = request.form.get('message', '')
        
        consultation = Consultation(
            name=name,
            email=email,
            date=datetime.strptime(date, '%Y-%m-%d'),
            message=message,
            user_id=session.get('user_id')
        )
        db.session.add(consultation)
        db.session.commit()
        return render_template('book_consultation.html', success=True)
    return render_template('book_consultation.html')



# Add this to your skin_analysis route function to help debug
@app.route('/skin-analysis', methods=['GET', 'POST'])
def skin_analysis():
    try:
        if request.method == 'GET':
            return render_template('skin_analysis.html')

        # Debug the incoming request
        print("Request Content-Type:", request.content_type)
        
        # Handle JSON-based request (camera images)
        if request.is_json:
            try:
                data = request.get_json()
                print("JSON data keys:", data.keys() if data else "None")
                if not data or 'images' not in data:
                    print("Missing images in JSON data")
                    return jsonify({'error': 'No image data received'}), 400
                
                print("Image positions received:", data['images'].keys())
            except Exception as e:
                print(f"JSON parsing error: {str(e)}")
                traceback.print_exc()
                return jsonify({'error': f'Error parsing JSON: {str(e)}'}), 400

            # Aggregate analyses
            overall_analysis = {
                'skin_type': {'type': None, 'confidence': 0},
                'conditions': {},
                'recommendations': {
                    'skincare_routine': {'morning': [], 'evening': []},
                    'products': {},
                    'lifestyle': []
                }
            }
            image_paths = {}
            
            for position, image_data in data['images'].items():
                try:
                    # Improved handling of different image data formats
                    if isinstance(image_data, str):
                        if image_data.startswith('data:image'):
                            # Extract the base64 encoded image data from the data URI
                            image_format, image_data_encoded = image_data.split(',', 1)
                            print(f"Image format: {image_format}")
                            image_bytes = base64.b64decode(image_data_encoded)
                        else:
                            # Handle plain base64 encoded image without data URI prefix
                            try:
                                image_bytes = base64.b64decode(image_data)
                            except Exception as e:
                                print(f"Base64 decoding error: {str(e)}")
                                # Try adding padding if needed
                                padding_needed = len(image_data) % 4
                                if padding_needed:
                                    image_data += '=' * (4 - padding_needed)
                                image_bytes = base64.b64decode(image_data)
                    else:
                        return jsonify({'error': f'Invalid image data format for position {position}'}), 400
                    
                    # Decode image
                    img_array = np.frombuffer(image_bytes, np.uint8)
                    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    
                    if img is None:
                        return jsonify({'error': f'Invalid image format for position {position}'}), 400
                    
                    # Enhanced face detection with multiple cascades and fallbacks
                    face_detected = False
                    
                    # Try the standard frontal face cascade first
                    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                    
                    if len(faces) == 0:
                        # Try alternative cascades if the first one fails
                        alt_cascades = [
                            'haarcascade_frontalface_alt.xml',
                            'haarcascade_frontalface_alt2.xml',
                            'haarcascade_profileface.xml'
                        ]
                        
                        for cascade_file in alt_cascades:
                            try:
                                alt_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + cascade_file)
                                faces = alt_cascade.detectMultiScale(gray, 1.1, 3)  # Slightly more tolerant parameters
                                if len(faces) > 0:
                                    face_detected = True
                                    print(f"Face detected with alternative cascade: {cascade_file}")
                                    break
                            except Exception as cascade_err:
                                print(f"Error with cascade {cascade_file}: {str(cascade_err)}")
                                continue
                    else:
                        face_detected = True
                    
                    # If still no face detected, try one more time with more relaxed parameters
                    if not face_detected:
                        faces = face_cascade.detectMultiScale(gray, 1.05, 2, minSize=(30, 30))
                        face_detected = len(faces) > 0
                    
                    # Allow processing to continue even if no face is detected
                    if not face_detected:
                        print(f"Warning: No face detected in the image for position {position}. Continuing anyway.")
                    
                    # Improved image enhancement pipeline
                    # 1. Apply adaptive enhancement based on image brightness
                    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                    brightness = np.mean(hsv[:,:,2])
                    print(f"Image brightness for position {position}: {brightness}")
                    
                    # Apply different enhancement based on brightness level
                    if brightness < 80:
                        # Low light conditions - stronger enhancement
                        # Increase brightness
                        hsv[:,:,2] = np.clip(hsv[:,:,2] * 1.4, 0, 255)
                        img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
                        
                        # Stronger sharpening for low light
                        kernel = np.array([[0, -1, 0], [-1, 5.8, -1], [0, -1, 0]])
                        img = cv2.filter2D(img, -1, kernel)
                        
                        # Stronger CLAHE for low light
                        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                        l, a, b = cv2.split(lab)
                        clahe = cv2.createCLAHE(clipLimit=4.5, tileGridSize=(8, 8))
                        l = clahe.apply(l)
                        enhanced_lab = cv2.merge((l, a, b))
                        img = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
                    else:
                        # Standard enhancement for normal lighting
                        kernel = np.array([[0, -1, 0], [-1, 5.2, -1], [0, -1, 0]])
                        img = cv2.filter2D(img, -1, kernel)
                        
                        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                        l, a, b = cv2.split(lab)
                        clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
                        l = clahe.apply(l)
                        enhanced_lab = cv2.merge((l, a, b))
                        img = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
                    
                    # Apply adaptive denoising based on image quality
                    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
                    if laplacian_var < 100:  # Higher noise or lower detail
                        img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
                    else:  # Better quality image
                        img = cv2.fastNlMeansDenoisingColored(img, None, 5, 5, 7, 21)
                    
                    # Save the enhanced image
                    filename = f"{uuid.uuid4()}.jpg"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    cv2.imwrite(filepath, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
                    
                    # Run skin analysis
                    analysis_result = analyze_skin_image(filepath)
                    image_paths[position] = f"/static/uploads/{filename}"
                    
                    # Merge analysis results
                    if analysis_result['skin_type']['confidence'] > overall_analysis['skin_type']['confidence']:
                        overall_analysis['skin_type'] = analysis_result['skin_type']

                    for condition, details in analysis_result['conditions'].items():
                        if details['detected']:
                            if condition not in overall_analysis['conditions'] or details['confidence'] > overall_analysis['conditions'].get(condition, {}).get('confidence', 0):
                                overall_analysis['conditions'][condition] = details

                    for routine in ['morning', 'evening']:
                        overall_analysis['recommendations']['skincare_routine'][routine] = list(set(
                            overall_analysis['recommendations']['skincare_routine'][routine] + 
                            analysis_result['recommendations']['skincare_routine'][routine]
                        ))

                    overall_analysis['recommendations']['products'].update(
                        analysis_result['recommendations']['products']
                    )

                    overall_analysis['recommendations']['lifestyle'] = list(set(
                        overall_analysis['recommendations']['lifestyle'] + 
                        analysis_result['recommendations']['lifestyle']
                    ))
                
                except Exception as e:
                    print(f"Error processing image for position {position}: {str(e)}")
                    traceback.print_exc()
                    return jsonify({'error': f'Error processing image for position {position}: {str(e)}'}), 400

            # Redirect to results page with analysis data
            return jsonify({
                'success': True,
                'redirect': url_for('analysis_results', 
                              image_paths=base64.b64encode(json.dumps(image_paths).encode()).decode(),
                              analysis=base64.b64encode(json.dumps(overall_analysis).encode()).decode())
            })

        # Handle form-based file upload with multiple views
        elif 'file-upload-front' in request.files:
            views = {'front': 'file-upload-front', 'left': 'file-upload-left', 'right': 'file-upload-right'}
            image_paths = {}
            
            # Process each uploaded view
            for position, field_name in views.items():
                file = request.files.get(field_name)
                
                if file and file.filename != '':
                    if not allowed_file(file.filename):
                        return render_template('skin_analysis.html', 
                                              error=f'Invalid file type for {position} view. Please upload a JPG, JPEG, or PNG image.')
                    
                    # Save the uploaded file temporarily
                    temp_filename = secure_filename(f"temp_{uuid.uuid4()}.{file.filename.rsplit('.', 1)[1].lower()}")
                    temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
                    file.save(temp_filepath)
                    
                    try:
                        # Process the image
                        img = cv2.imread(temp_filepath)
                        if img is None:
                            os.remove(temp_filepath)
                            continue
                        
                        # Process image (same enhancement as above)
                        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        
                        # Check brightness and apply adaptive enhancement
                        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                        brightness = np.mean(hsv[:,:,2])
                        
                        if brightness < 80:
                            # Low light enhancement
                            hsv[:,:,2] = np.clip(hsv[:,:,2] * 1.4, 0, 255)
                            img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
                            kernel = np.array([[0, -1, 0], [-1, 5.8, -1], [0, -1, 0]])
                            img = cv2.filter2D(img, -1, kernel)
                            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                            l, a, b = cv2.split(lab)
                            clahe = cv2.createCLAHE(clipLimit=4.5, tileGridSize=(8, 8))
                            l = clahe.apply(l)
                            enhanced_lab = cv2.merge((l, a, b))
                            img = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
                        else:
                            # Standard enhancement
                            kernel = np.array([[0, -1, 0], [-1, 5.2, -1], [0, -1, 0]])
                            img = cv2.filter2D(img, -1, kernel)
                            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                            l, a, b = cv2.split(lab)
                            clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
                            l = clahe.apply(l)
                            enhanced_lab = cv2.merge((l, a, b))
                            img = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
                        
                        # Apply adaptive denoising
                        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
                        if laplacian_var < 100:
                            img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
                        else:
                            img = cv2.fastNlMeansDenoisingColored(img, None, 5, 5, 7, 21)
                        
                        # Save the enhanced image with a proper name
                        filename = secure_filename(f"{uuid.uuid4()}.{file.filename.rsplit('.', 1)[1].lower()}")
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        cv2.imwrite(filepath, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
                        
                        # Store the path
                        image_paths[position] = f"/static/uploads/{filename}"
                        
                        # Remove the temporary file
                        if os.path.exists(temp_filepath):
                            os.remove(temp_filepath)
                            
                    except Exception as e:
                        if os.path.exists(temp_filepath):
                            os.remove(temp_filepath)
                        print(f"Error processing {position} view: {str(e)}")
                        traceback.print_exc()
                        return render_template('skin_analysis.html', error=f'Error processing {position} view: {str(e)}')
            
            if not image_paths:
                return render_template('skin_analysis.html', error='No valid images were uploaded')
            
            # Aggregate analyses from all views
            overall_analysis = {
                'skin_type': {'type': None, 'confidence': 0},
                'conditions': {},
                'recommendations': {
                    'skincare_routine': {'morning': [], 'evening': []},
                    'products': {},
                    'lifestyle': []
                }
            }
            
            for position, img_path in image_paths.items():
                # Get the full file path from the web path
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(img_path))
                analysis_result = analyze_skin_image(filepath)
                
                # Merge analysis results (same logic as above)
                if analysis_result['skin_type']['confidence'] > overall_analysis['skin_type']['confidence']:
                    overall_analysis['skin_type'] = analysis_result['skin_type']

                for condition, details in analysis_result['conditions'].items():
                    if details['detected']:
                        if condition not in overall_analysis['conditions'] or details['confidence'] > overall_analysis['conditions'].get(condition, {}).get('confidence', 0):
                            overall_analysis['conditions'][condition] = details

                for routine in ['morning', 'evening']:
                    overall_analysis['recommendations']['skincare_routine'][routine] = list(set(
                        overall_analysis['recommendations']['skincare_routine'][routine] + 
                        analysis_result['recommendations']['skincare_routine'][routine]
                    ))

                overall_analysis['recommendations']['products'].update(
                    analysis_result['recommendations']['products']
                )

                overall_analysis['recommendations']['lifestyle'] = list(set(
                    overall_analysis['recommendations']['lifestyle'] + 
                    analysis_result['recommendations']['lifestyle']
                ))
            
            return redirect(url_for('analysis_results',
                                  image_paths=base64.b64encode(json.dumps(image_paths).encode()).decode(),
                                  analysis=base64.b64encode(json.dumps(overall_analysis).encode()).decode()))
                
        # Handle older format single image upload
        elif 'image' in request.files:
            file = request.files['image']
            if file.filename == '':
                return render_template('skin_analysis.html', error='No selected file')
            
            if not allowed_file(file.filename):
                return render_template('skin_analysis.html', error='Invalid file type. Please upload a JPG, JPEG, or PNG image.')
            
            # Similar processing as above for a single image
            # Implement the same image enhancement pipeline as above
            # ...

        # No valid input found
        return render_template('skin_analysis.html', error='No valid image received')

    except Exception as e:
        traceback.print_exc()
        return render_template('skin_analysis.html', error=f'An unexpected error occurred: {str(e)}')
    
@app.route('/analysis-results')
def analysis_results():
    try:
        # Retrieve and decode image paths
        image_paths_encoded = request.args.get('image_paths', '')
        if image_paths_encoded:
            try:
                image_paths = json.loads(base64.b64decode(image_paths_encoded.encode()).decode())
            except Exception as e:
                print(f"Image paths decode error: {e}")
                image_paths = {}
        else:
            image_paths = {}

        # Retrieve and decode analysis data
        analysis_encoded = request.args.get('analysis', '')
        if analysis_encoded:
            try:
                analysis = json.loads(base64.b64decode(analysis_encoded.encode()).decode())
            except Exception as e:
                print(f"Analysis decode error: {e}")
                analysis = {}
        else:
            analysis = {}

        # Additional error checking
        if not image_paths or not analysis:
            return render_template('analysis_results.html', 
                                   error="No analysis data available",
                                   image_paths={},
                                   analysis={})

        # Save progress if user is logged in
        if 'user_id' in session:
            for path in image_paths.values():
                save_progress(session['user_id'], path, analysis)

        return render_template('analysis_results.html', 
                               image_paths=image_paths,
                               analysis=analysis)

    except Exception as e:
        traceback.print_exc()
        return render_template('analysis_results.html',
                               error=f"Unexpected error: {str(e)}",
                               image_paths={},
                               analysis={})
@app.route('/progress')
def progress():
    if 'user_id' not in session:
        return redirect(url_for('signin'))
    
    try:
        progress_entries = Progress.query.filter_by(
            user_id=session['user_id']
        ).order_by(
            Progress.timestamp.desc()
        ).all()
        
        # Calculate improvements
        for i in range(len(progress_entries)):
            if i < len(progress_entries) - 1:
                current = progress_entries[i]
                previous = progress_entries[i + 1]
        
        # Compare skin scores if they exist and previous score is non-zero
                if (current.skin_score is not None and 
                    previous.skin_score is not None and 
                    previous.skin_score != 0):
                    improvement = ((current.skin_score - previous.skin_score) / previous.skin_score) * 100
                    current.improvement = round(improvement, 1)
                else:
                    current.improvement = None
        
        return render_template( 
            'progress.html',    
            progress=progress_entries,
            user_name=session.get('user_name', 'User')
        )
        
    except Exception as e:
        print(f"Error in progress route: {str(e)}")
        return render_template(
            'progress.html',
            progress=[],
            error="An error occurred while loading your progress data."
        )

# Update your analyze_skin_image function to save progress
def save_progress(user_id, image_path, analysis_result):
    try:
        # Extract relevant data from analysis result
        skin_type = analysis_result.get('skin_type', {}).get('type', 'Unknown')
        
        # Calculate a basic skin score
        skin_score = calculate_skin_score(analysis_result)
        
        # Extract conditions
        conditions = [
            condition for condition, details in analysis_result.get('conditions', {}).items()
            if details.get('detected', False)
        ]
        
        # Create new progress entry
        progress_entry = Progress(
            user_id=user_id,
            image_path=image_path,
            result='Analysis Complete',
            skin_type=skin_type,
            skin_score=skin_score
        )
        
        # Use setter methods
        progress_entry.set_conditions(conditions)
        progress_entry.set_analysis_data(analysis_result)
        
        db.session.add(progress_entry)
        db.session.commit()
        
        return True
        
    except Exception as e:
        print(f"Error saving progress: {str(e)}")
        db.session.rollback()
        return False
def calculate_skin_score(analysis_result):
    """
    Calculate a skin health score based on analysis results
    Returns a score from 0-100
    """
    try:
        base_score = 70  # Start with a base score
        
        # Adjust based on condition severities
        for condition, details in analysis_result.get('conditions', {}).items():
            if details.get('detected'):
                severity = details.get('severity', 'Mild').lower()
                if severity == 'severe':
                    base_score -= 15
                elif severity == 'moderate':
                    base_score -= 10
                elif severity == 'mild':
                    base_score -= 5
        
        # Ensure score stays within 0-100 range
        return max(0, min(100, base_score))
        
    except Exception as e:
        print(f"Error calculating skin score: {str(e)}")
        return 70
    
@app.route('/educational-hub')
def educational_hub():
    return render_template('educational_hub.html')

@app.route('/contact')
def contact_page():  # Renaming the function to avoid conflict
    return render_template('contact.html')

@app.route('/skin-types')
def skin_types():
    return render_template('skin-types.html')

@app.route('/skin-basics')
def skin_basics():
    return render_template('skincare-basics.html')

@app.route('/skin-concerns')
def skin_concerns():
    return render_template('skin-concerns.html')

# Add this to your app.py or in a separate database initialization script
with app.app_context():
    # Drop all existing tables
    db.drop_all()
    
    # Recreate all tables
    db.create_all()
    print("Database tables recreated successfully.")
    
if __name__ == '__main__':
    app.run(debug=True)