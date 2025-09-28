import face_recognition
import numpy as np
import cv2
from PIL import Image
import io
import base64
import logging
from typing import Optional, List, Tuple
from django.core.files.uploadedfile import InMemoryUploadedFile

logger = logging.getLogger(__name__)


class FaceRecognitionError(Exception):
    """Custom exception for face recognition errors"""
    pass


class FaceRecognitionUtils:
    """Utility class for face recognition operations"""
    
    # Configuration constants
    FACE_CONFIDENCE_THRESHOLD = 0.6  # Lower values = more strict matching
    MAX_IMAGE_SIZE = (800, 600)  # Resize large images for faster processing
    ENCODING_MODEL = 'large'  # 'small' for faster, 'large' for more accurate
    
    @staticmethod
    def preprocess_image(image_file) -> np.ndarray:
        """
        Preprocess uploaded image for face recognition
        
        Args:
            image_file: Django uploaded file or file path
            
        Returns:
            numpy array representing the image in RGB format
            
        Raises:
            FaceRecognitionError: If image cannot be processed
        """
        try:
            if isinstance(image_file, InMemoryUploadedFile):
                # Handle uploaded file
                image_data = image_file.read()
                image = Image.open(io.BytesIO(image_data))
            elif isinstance(image_file, str):
                # Handle file path
                image = Image.open(image_file)
            else:
                # Handle file-like object
                image = Image.open(image_file)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if image is too large
            if image.size[0] > FaceRecognitionUtils.MAX_IMAGE_SIZE[0] or \
               image.size[1] > FaceRecognitionUtils.MAX_IMAGE_SIZE[1]:
                image.thumbnail(FaceRecognitionUtils.MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
            
            # Convert to numpy array
            return np.array(image)
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            raise FaceRecognitionError(f"Failed to process image: {str(e)}")
    
    @staticmethod
    def detect_faces(image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in an image with enhanced detection parameters
        
        Args:
            image: numpy array representing the image in RGB format
            
        Returns:
            List of face locations as (top, right, bottom, left) tuples
        """
        try:
            # Convert to grayscale for face detection (faster and often more reliable)
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # Apply histogram equalization to improve contrast
            gray = cv2.equalizeHist(gray)
            
            # Try multiple detection methods for better accuracy
            face_locations = []
            
            # Method 1: HOG (faster, works well in good lighting)
            try:
                face_locations = face_recognition.face_locations(
                    gray,
                    model='hog',
                    number_of_times_to_upsample=3  # Look harder for faces
                )
            except Exception as e:
                logger.warning(f"HOG face detection failed: {str(e)}")
            
            # If no faces found with HOG, try CNN (slower but more accurate)
            if not face_locations:
                try:
                    face_locations = face_recognition.face_locations(
                        gray,
                        model='cnn',
                        number_of_times_to_upsample=1
                    )
                except Exception as e:
                    logger.warning(f"CNN face detection failed: {str(e)}")
            
            # If still no faces found, try with the original color image
            if not face_locations:
                try:
                    face_locations = face_recognition.face_locations(
                        image,
                        model='hog',
                        number_of_times_to_upsample=2
                    )
                except Exception as e:
                    logger.warning(f"Fallback face detection failed: {str(e)}")
            
            # If we still can't find faces, try with OpenCV's Haar Cascade as last resort
            if not face_locations:
                try:
                    # Load the pre-trained Haar Cascade classifier
                    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                    face_cascade = cv2.CascadeClassifier(cascade_path)
                    
                    # Detect faces
                    faces = face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.1,
                        minNeighbors=5,
                        minSize=(30, 30),
                        flags=cv2.CASCADE_SCALE_IMAGE
                    )
                    
                    # Convert to the format expected by face_recognition
                    for (x, y, w, h) in faces:
                        face_locations.append((y, x + w, y + h, x))
                except Exception as e:
                    logger.warning(f"Haar Cascade detection failed: {str(e)}")
            
            logger.info(f"Detected {len(face_locations)} face(s) in the image")
            return face_locations
            
        except Exception as e:
            logger.error(f"Error detecting faces: {str(e)}", exc_info=True)
            return []
    
    @staticmethod
    def generate_face_encoding(image: np.ndarray) -> Optional[np.ndarray]:
        """
        Generate face encoding from an image with enhanced validation and multiple attempts
        
        Args:
            image: numpy array representing the image in RGB format
            
        Returns:
            Face encoding as numpy array, or None if no valid face found
            
        Raises:
            FaceRecognitionError: If face detection or encoding fails
        """
        def try_generate_encoding(img, method: str = 'default') -> Optional[np.ndarray]:
            """Helper function to try generating encoding with different methods"""
            try:
                # Try with the detected face location
                face_locations = FaceRecognitionUtils.detect_faces(img)
                if not face_locations:
                    logger.warning(f"No faces detected using {method} method")
                    return None
                
                # Use the largest face found
                face_location = max(face_locations, key=lambda loc: (loc[2]-loc[0])*(loc[1]-loc[3]))
                
                # Generate encoding with multiple jitters for better accuracy
                encodings = face_recognition.face_encodings(
                    img,
                    known_face_locations=[face_location],
                    model=FaceRecognitionUtils.ENCODING_MODEL,
                    num_jitters=5,  # Higher number for better accuracy
                )
                
                if not encodings:
                    logger.warning(f"No encodings generated using {method} method")
                    return None
                    
                return encodings[0]
                
            except Exception as e:
                logger.warning(f"Encoding attempt with {method} method failed: {str(e)}")
                return None
        
        try:
            # Input validation
            if image is None or not isinstance(image, np.ndarray):
                raise FaceRecognitionError("Invalid image input")
                
            if image.size == 0:
                raise FaceRecognitionError("Empty image provided")
            
            # Ensure image is in RGB format
            if len(image.shape) != 3 or image.shape[2] != 3:
                raise FaceRecognitionError("Image must be in RGB format")
            
            # Try multiple methods to generate encoding
            methods = [
                ('default', image),  # Original image
                ('equalized', cv2.equalizeHist(cv2.cvtColor(image, cv2.COLOR_RGB2GRAY))),
                ('clahe', cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(
                    cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                ))
            ]
            
            for method_name, img in methods:
                if len(img.shape) == 2:  # If grayscale, convert to RGB
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
                
                encoding = try_generate_encoding(img, method_name)
                if encoding is not None:
                    logger.info(f"Successfully generated encoding using {method_name} method")
                    return encoding
            
            # If all methods failed, try with the original image one more time with CNN model
            try:
                face_locations = face_recognition.face_locations(
                    image,
                    model='cnn',
                    number_of_times_to_upsample=1
                )
                
                if face_locations:
                    encodings = face_recognition.face_encodings(
                        image,
                        known_face_locations=face_locations,
                        model='large',
                        num_jitters=10
                    )
                    if encodings:
                        return encodings[0]
            except Exception as e:
                logger.warning(f"Final CNN-based encoding attempt failed: {str(e)}")
            
            logger.warning("All face encoding attempts failed")
            return None
            
        except Exception as e:
            logger.error(f"Error in generate_face_encoding: {str(e)}", exc_info=True)
            return None
    
    @staticmethod
    def compare_faces(known_encoding_str: str, face_encoding_to_check: np.ndarray) -> Tuple[bool, float]:
        """
        Compare a face encoding to a known encoding with enhanced validation
        and multiple comparison strategies for better accuracy.
        
        Args:
            known_encoding_str: The known face encoding as a base64 string
            face_encoding_to_check: The face encoding to compare against (numpy array)
            
        Returns:
            Tuple of (match: bool, confidence: float)
        """
        def normalize_encoding(encoding):
            """Normalize encoding to unit vector for better comparison"""
            norm = np.linalg.norm(encoding)
            if norm == 0:
                return encoding
            return encoding / norm
            
        def calculate_similarity(enc1, enc2, method='cosine'):
            """Calculate similarity between two encodings using different methods"""
            try:
                if method == 'cosine':
                    # Cosine similarity (works well for face recognition)
                    return np.dot(enc1, enc2) / (np.linalg.norm(enc1) * np.linalg.norm(enc2))
                else:  # euclidean
                    # Euclidean distance (inverted and scaled to 0-1)
                    return 1.0 / (1.0 + np.linalg.norm(enc1 - enc2))
            except Exception as e:
                logger.warning(f"Error in {method} similarity calculation: {str(e)}")
                return 0.0
        
        try:
            # Input validation
            if not known_encoding_str or not face_encoding_to_check.any():
                logger.warning("Invalid input for face comparison")
                return False, 0.0
            
            # Convert the stored string back to numpy array
            try:
                known_encoding = np.frombuffer(
                    base64.b64decode(known_encoding_str.encode('utf-8')),
                    dtype=np.float64
                )
                
                # Ensure the encoding is valid
                if known_encoding.size == 0 or np.all(known_encoding == 0):
                    logger.error("Invalid known encoding (all zeros)")
                    return False, 0.0
                    
            except Exception as e:
                logger.error(f"Failed to decode stored face encoding: {str(e)}", exc_info=True)
                return False, 0.0
            
            # Validate encoding shapes
            if known_encoding.shape != face_encoding_to_check.shape:
                logger.warning(f"Encoding shape mismatch: {known_encoding.shape} vs {face_encoding_to_check.shape}")
                return False, 0.0
            
            # Normalize encodings for better comparison
            known_norm = normalize_encoding(known_encoding)
            check_norm = normalize_encoding(face_encoding_to_check)
            
            # Calculate similarities using different methods
            cosine_sim = calculate_similarity(known_norm, check_norm, 'cosine')
            euclidean_sim = calculate_similarity(known_encoding, face_encoding_to_check, 'euclidean')
            
            # Calculate final confidence (weighted average)
            confidence = (cosine_sim * 0.7 + euclidean_sim * 0.3) * 100
            confidence = max(0.0, min(100.0, confidence))  # Clamp to 0-100%
            
            # Calculate face distance for logging
            face_distance = face_recognition.face_distance(
                [known_encoding], 
                face_encoding_to_check
            )[0]
            
            # Dynamic threshold based on confidence
            dynamic_threshold = FaceRecognitionUtils.FACE_CONFIDENCE_THRESHOLD
            
            # If the face is very clear (high confidence in detection), be more strict
            if confidence > 70:  # If we're very confident in the detection
                dynamic_threshold *= 0.9  # 10% stricter threshold
            
            # Determine match based on dynamic threshold
            match = face_distance <= dynamic_threshold
            
            logger.info(
                f"Face comparison - "
                f"Distance: {face_distance:.4f}, "
                f"Confidence: {confidence:.2f}%, "
                f"Match: {match}, "
                f"Threshold: {dynamic_threshold:.4f}"
            )
            
            return match, confidence
            
        except Exception as e:
            logger.error(f"Unexpected error in compare_faces: {str(e)}", exc_info=True)
            return False, 0.0
    
    @staticmethod
    def encoding_to_string(encoding: np.ndarray) -> str:
        """
        Convert face encoding to string for database storage
        
        Args:
            encoding: Face encoding as numpy array
            
        Returns:
            Base64 encoded string representation
        """
        try:
            # Convert to bytes and then to base64 string
            encoding_bytes = encoding.tobytes()
            encoding_string = base64.b64encode(encoding_bytes).decode('utf-8')
            return encoding_string
        except Exception as e:
            logger.error(f"Error converting encoding to string: {str(e)}")
            raise FaceRecognitionError(f"Failed to convert encoding: {str(e)}")
    
    @staticmethod
    def string_to_encoding(encoding_string: str) -> np.ndarray:
        """
        Convert string back to face encoding
        
        Args:
            encoding_string: Base64 encoded string
            
        Returns:
            Face encoding as numpy array
        """
        try:
            # Decode from base64 and convert back to numpy array
            encoding_bytes = base64.b64decode(encoding_string.encode('utf-8'))
            encoding = np.frombuffer(encoding_bytes, dtype=np.float64)
            return encoding
        except Exception as e:
            logger.error(f"Error converting string to encoding: {str(e)}")
            raise FaceRecognitionError(f"Failed to convert string to encoding: {str(e)}")
    
    @staticmethod
    def setup_user_face_recognition(user, image_file) -> Tuple[bool, str, float]:
        """
        Set up face recognition for a user
        
        Args:
            user: User model instance
            image_file: Uploaded image file
            
        Returns:
            Tuple of (success, message, confidence)
        """
        try:
            # Preprocess image
            image = FaceRecognitionUtils.preprocess_image(image_file)
            
            # Generate face encoding
            encoding = FaceRecognitionUtils.generate_face_encoding(image)
            
            # Convert encoding to string and save to user
            encoding_string = FaceRecognitionUtils.encoding_to_string(encoding)
            user.face_encoding = encoding_string
            user.save()
            
            logger.info(f"Face recognition setup completed for user {user.employee_id}")
            return True, "Face recognition setup successful", 1.0
            
        except FaceRecognitionError as e:
            logger.warning(f"Face recognition setup failed for user {user.employee_id}: {str(e)}")
            return False, str(e), 0.0
        except Exception as e:
            logger.error(f"Unexpected error in face recognition setup for user {user.employee_id}: {str(e)}")
            return False, "An unexpected error occurred during setup", 0.0
    
    @staticmethod
    def verify_user_face(user, image_file) -> Tuple[bool, str, float]:
        """
        Verify user's face against stored encoding
        
        Args:
            user: User model instance
            image_file: Uploaded image file for verification
            
        Returns:
            Tuple of (is_verified, message, confidence_score)
        """
        try:
            # Check if user has face encoding set up
            if not user.face_encoding:
                return False, "Face recognition not set up for this user", 0.0
            
            # Preprocess the uploaded image
            image = FaceRecognitionUtils.preprocess_image(image_file)
            
            # Generate encoding for the uploaded image
            unknown_encoding = FaceRecognitionUtils.generate_face_encoding(image)
            
            # Get stored encoding
            known_encoding = FaceRecognitionUtils.string_to_encoding(user.face_encoding)
            
            # Compare faces
            is_match, confidence = FaceRecognitionUtils.compare_faces(known_encoding, unknown_encoding)
            
            if is_match:
                logger.info(f"Face verification successful for user {user.employee_id} with confidence {confidence:.2f}")
                return True, "Face verification successful", confidence
            else:
                logger.warning(f"Face verification failed for user {user.employee_id} with confidence {confidence:.2f}")
                return False, "Face verification failed", confidence
                
        except FaceRecognitionError as e:
            logger.warning(f"Face verification error for user {user.employee_id}: {str(e)}")
            return False, str(e), 0.0
        except Exception as e:
            logger.error(f"Unexpected error in face verification for user {user.employee_id}: {str(e)}")
            return False, "An unexpected error occurred during verification", 0.0
    
    @staticmethod
    def enhance_image_quality(image: np.ndarray) -> np.ndarray:
        """
        Enhance image quality for better face recognition
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Enhanced image as numpy array
        """
        try:
            # Convert to grayscale for processing
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # Apply histogram equalization to improve contrast
            enhanced_gray = cv2.equalizeHist(gray)
            
            # Convert back to RGB
            enhanced_image = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2RGB)
            
            return enhanced_image
            
        except Exception as e:
            logger.warning(f"Image enhancement failed: {str(e)}, using original image")
            return image
