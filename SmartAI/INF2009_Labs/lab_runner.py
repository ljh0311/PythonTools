import subprocess
import time
import cv2
import os
from datetime import datetime
import numpy as np
import torch
import sys
import traceback
import select
import platform
from torchvision.models import mobilenet_v2

class LabRunnerError(Exception):
    """Custom exception for LabRunner errors"""
    pass

class LabRunner:
    def __init__(self, output_md_file="lab_results.md"):
        self.output_md_file = output_md_file
        self.results = []
        self.temp_md_file = f"temp_{output_md_file}"
        self.debug_mode = True
        self.use_test_image = False
        
        # Check platform compatibility
        self.check_platform_compatibility()
        
        # Validate environment and setup
        self.validate_environment()
        self.setup_output_file()

    def check_platform_compatibility(self):
        """Check if running on supported platform"""
        system = platform.system()
        if system == "Windows":
            print("\nNOTE: Running on Windows environment")
            print("1. Basic MobileNet test will be executed")
            print("2. Post-training quantization will be demonstrated")
            print("3. Some features may be limited compared to Raspberry Pi\n")
            self.is_windows = True
            self.quantization_engine = "onednn"  # Use onednn for Windows
        elif system == "Linux":
            # Check if running on Raspberry Pi
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    if 'Raspberry Pi' in f.read():
                        print("\nNOTE: Running on Raspberry Pi")
                        print("Full test suite will be executed including:")
                        print("1. Basic MobileNet")
                        print("2. Quantized MobileNet")
                        print("3. Real-time predictions\n")
                        self.is_raspberry_pi = True
                        self.quantization_engine = "qnnpack"  # Use qnnpack for Raspberry Pi
                    else:
                        self.is_raspberry_pi = False
                        self.quantization_engine = "onednn"
            except:
                self.is_raspberry_pi = False
                self.quantization_engine = "onednn"
        else:
            self.is_windows = False
            self.is_raspberry_pi = False
            self.quantization_engine = "onednn"

    def setup_output_file(self):
        """Initialize the markdown file with header"""
        header = f"""# Lab Results - Deep Learning on Edge
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Environment Information
- Platform: {platform.system()} {platform.release()}
- Python Version: {sys.version.split()[0]}
- PyTorch Version: {torch.__version__}
- CUDA Available: {torch.cuda.is_available()}
- OpenCV Version: {cv2.__version__}
- Quantization Engine: {self.quantization_engine}
- Running on Raspberry Pi: {getattr(self, 'is_raspberry_pi', False)}
"""
        with open(self.temp_md_file, 'w') as f:
            f.write(header)

    def debug_print(self, message):
        """Print debug information if debug mode is enabled"""
        if self.debug_mode:
            print(f"[DEBUG] {message}")

    def validate_environment(self):
        """Validate the environment before running tests"""
        self.debug_print("Validating environment...")
        
        try:
            import torch
            import torchvision
            self.debug_print(f"PyTorch version: {torch.__version__}")
            self.debug_print(f"Torchvision version: {torchvision.__version__}")
            
            # Check if running on Windows
            if self.is_windows:
                self.debug_print("WARNING: Running on Windows - quantization features will be limited")
            
            # Check if MobileNetV2 is available
            if self.is_windows:
                from torchvision.models import mobilenet_v2
            else:
                from torchvision.models.quantization import MobileNet_V2_QuantizedWeights
            
            self.debug_print("MobileNetV2 model is available")
            
        except ImportError as e:
            raise LabRunnerError(f"Required packages not installed: {str(e)}")
        
        # Check OpenCV and camera
        try:
            import cv2
            self.debug_print(f"OpenCV version: {cv2.__version__}")
            
            # Test camera access
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                self.debug_print("Warning: Could not open camera. Will modify script to use test image instead.")
                self.use_test_image = True
            else:
                self.debug_print("Camera access successful")
                ret, frame = cap.read()
                if not ret:
                    self.debug_print("Warning: Could not read frame. Will use test image instead.")
                    self.use_test_image = True
                else:
                    self.debug_print(f"Successfully captured frame of size {frame.shape}")
                    self.use_test_image = False
            cap.release()
        except Exception as e:
            self.debug_print(f"Camera check failed: {str(e)}")
            self.use_test_image = True

    def modify_script_for_testing(self, content):
        """Modify the script to work without camera if needed"""
        # Add debug prints to the script
        debug_imports = """
import sys
import traceback

def debug_print(msg):
    print(f"[SCRIPT DEBUG] {msg}", flush=True)

debug_print("Script starting...")
"""
        modified_content = debug_imports + content

        # Add error handling around model loading
        model_load_wrapper = """
try:
    debug_print("Loading MobileNetV2 model...")
    weights = MobileNet_V2_QuantizedWeights.DEFAULT
    classes = weights.meta["categories"]
    net = models.quantization.mobilenet_v2(pretrained=True, quantize=quantize)
    debug_print("Model loaded successfully")
except Exception as e:
    debug_print(f"Error loading model: {str(e)}")
    traceback.print_exc()
    sys.exit(1)
"""
        modified_content = modified_content.replace(
            'weights = MobileNet_V2_QuantizedWeights.DEFAULT\nclasses = weights.meta["categories"]\nnet = models.quantization.mobilenet_v2(pretrained=True, quantize=quantize)',
            model_load_wrapper
        )

        # Add progress prints
        modified_content = modified_content.replace(
            'while True:',
            'while True:\n    debug_print("Processing frame...")'
        )

        if self.use_test_image:
            # Add imports
            modified_content = "import os\n" + modified_content
            
            # Replace camera capture with test image
            camera_setup = """
debug_print("Creating test image...")
# Create a test image instead of using camera
test_image = np.zeros((224, 224, 3), dtype=np.uint8)
cv2.putText(test_image, 'Test', (10, 112), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
debug_print("Test image created")
"""
            modified_content = modified_content.replace(
                'cap = cv2.VideoCapture(0)',
                camera_setup
            )
            
            # Replace frame reading
            modified_content = modified_content.replace(
                'ret, image = cap.read()',
                'image = test_image.copy()\ndebug_print("Using test image frame")'
            )
            
        return modified_content

    def check_output_validity(self, stdout, stderr):
        """Check if the output indicates successful execution"""
        self.debug_print("\n=== Output Analysis ===")
        self.debug_print("STDOUT:")
        self.debug_print(stdout)
        self.debug_print("\nSTDERR:")
        self.debug_print(stderr)
        
        # Check for critical error patterns
        critical_errors = [
            "RuntimeError: quantized engine QNNPACK is not supported",
            "ModuleNotFoundError",
            "ImportError",
            "RuntimeError: CUDA",
            "cannot import name",
            "No module named",
            "failed to read frame",
            "Error loading model",
            "Error occurred:",
            "Traceback"
        ]
        
        for error in critical_errors:
            if error in (stdout + stderr):
                self.debug_print(f"Found critical error: {error}")
                raise LabRunnerError(f"Critical error detected: {error}")

        return True  # We now check for FPS in the run_mobile_net function

    def run_mobile_net(self, quantize=False, show_predictions=False):
        """Run mobile_net.py with different configurations"""
        self.debug_print(f"\n=== Running MobileNet (quantize={quantize}, predictions={show_predictions}) ===")
        
        try:
            with open('Codes/mobile_net.py', 'r') as f:
                content = f.read()
                self.debug_print("Successfully read mobile_net.py")
        except Exception as e:
            raise LabRunnerError(f"Could not read mobile_net.py: {str(e)}")
        
        # Add exit after we get some FPS measurements
        fps_counter_code = '''
        # FPS measurement counter
        fps_measurements = 0
        '''
        
        # Insert the counter code after the frame_count initialization
        modified_content = content.replace(
            'frame_count = 0',
            'frame_count = 0' + fps_counter_code
        )
        
        # Modify the FPS logging section to count measurements
        fps_logging_code = '''            print(f"============={frame_count / (now-last_logged)} fps =================")
            fps_measurements += 1
            if fps_measurements >= 3:  # Exit after getting 3 FPS measurements
                print("Completed FPS measurements")
                break
            last_logged = now
            frame_count = 0'''
        
        # Replace the original FPS logging code
        modified_content = modified_content.replace(
            '''            print(
                f"============={frame_count / (now-last_logged)} fps ================="
            )
            last_logged = now
            frame_count = 0''',
            fps_logging_code
        )
        
        # Modify the content based on parameters
        modified_content = modified_content.replace('quantize = False', f'quantize = {quantize}')
        if show_predictions:
            # Find and uncomment the prediction block
            prediction_block = """        # Uncomment below 5 lines to print top 10 predictions
        # top = list(enumerate(output[0].softmax(dim=0)))
        # top.sort(key=lambda x: x[1], reverse=True)
        # for idx, val in top[:10]:
        #    print(f"{val.item()*100:.2f}% {classes[idx]}")
        # print(f"========================================================================")"""
            
            uncommented_block = """        # Print top 10 predictions
        top = list(enumerate(output[0].softmax(dim=0)))
        top.sort(key=lambda x: x[1], reverse=True)
        for idx, val in top[:10]:
            print(f"{val.item()*100:.2f}% {classes[idx]}")
        print(f"========================================================================")"""
            
            modified_content = modified_content.replace(prediction_block, uncommented_block)
        
        # Save temporary file
        temp_file = 'temp_mobile_net.py'
        with open(temp_file, 'w') as f:
            f.write(modified_content)
            self.debug_print(f"Saved modified script to {temp_file}")
            
        # Debug: Print the modified content
        self.debug_print("Modified script content:")
        self.debug_print(modified_content)

        # Run the script
        try:
            start_time = time.time()
            self.debug_print("Starting process execution...")
            
            # Run with unbuffered output
            process = subprocess.Popen(
                ['python', '-u', temp_file],  # -u for unbuffered output
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                env=dict(os.environ, PYTHONUNBUFFERED="1")  # Force unbuffered output
            )
            
            output = []
            errors = []
            fps_found = False
            
            # Monitor output in real-time
            while True:
                # Read stdout
                line = process.stdout.readline()
                if line:
                    output.append(line)
                    self.debug_print(f"Output: {line.strip()}")
                    if 'fps' in line.lower():
                        fps_found = True
                
                # Read stderr
                err = process.stderr.readline()
                if err:
                    errors.append(err)
                    self.debug_print(f"Error: {err.strip()}")
                
                # Check if process has finished
                if process.poll() is not None:
                    # Get any remaining output
                    for line in process.stdout:
                        output.append(line)
                        self.debug_print(f"Output: {line.strip()}")
                        if 'fps' in line.lower():
                            fps_found = True
                    for err in process.stderr:
                        errors.append(err)
                        self.debug_print(f"Error: {err.strip()}")
                    break
                
                # Check if we've been running too long
                if time.time() - start_time > 60:  # Increased timeout to 60 seconds
                    self.debug_print("Process timeout reached")
                    process.terminate()
                    break
            
            stdout = ''.join(output)
            stderr = ''.join(errors)
            duration = time.time() - start_time
            
            self.debug_print(f"Process completed with return code: {process.returncode}")
            
            # Check if we got any FPS output
            if fps_found:
                result = {
                    'configuration': 'Quantized' if quantize else 'Non-quantized',
                    'predictions_enabled': show_predictions,
                    'output': stdout,
                    'errors': stderr,
                    'duration': duration
                }
                self.add_result_to_md(result)
                return True
            else:
                self.debug_print("No FPS output found in process output")
                return False
            
        except Exception as e:
            self.debug_print(f"Unexpected error: {str(e)}")
            self.debug_print(traceback.format_exc())
            return False
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                self.debug_print(f"Cleaned up {temp_file}")

    def capture_screenshot(self, window_name="MobileNet Demo"):
        """Capture screenshot of the OpenCV window"""
        try:
            # Wait for window to be available
            time.sleep(2)
            window = cv2.getWindowByName(window_name)
            if window is not None:
                screenshot = np.zeros((480, 640, 3), np.uint8)  # Adjust size as needed
                cv2.imshow(window_name, screenshot)
                screenshot_path = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                cv2.imwrite(screenshot_path, screenshot)
                return screenshot_path
            return None
        except Exception as e:
            print(f"Screenshot capture failed: {str(e)}")
            return None

    def add_result_to_md(self, result):
        """Add a result section to the markdown file"""
        with open(self.temp_md_file, 'a') as f:
            f.write(f"\n## Test Configuration: {result['configuration']}\n")
            f.write(f"- Predictions Enabled: {result['predictions_enabled']}\n")
            f.write(f"- Duration: {result['duration']:.2f} seconds\n")
            
            if result['output']:
                f.write("\n### Output:\n```\n")
                f.write(result['output'])
                f.write("\n```\n")
            
            if result['errors']:
                f.write("\n### Warnings and Info:\n```\n")
                f.write(result['errors'])
                f.write("\n```\n")

    def run_test(self, script_name):
        """Run a test script and capture its output"""
        self.debug_print(f"\nRunning {script_name}...")
        
        try:
            # Run the script and capture output
            process = subprocess.Popen(
                ['python3', script_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=dict(os.environ, PYTHONUNBUFFERED="1")
            )
            
            output = []
            errors = []
            fps_values = []
            
            # Monitor output in real-time
            while True:
                # Read stdout
                line = process.stdout.readline()
                if line:
                    output.append(line)
                    self.debug_print(f"Output: {line.strip()}")
                    # Extract FPS if present
                    if 'fps' in line.lower():
                        try:
                            fps = float(line.split('=')[1].strip(' fps='))
                            fps_values.append(fps)
                        except:
                            pass
                
                # Read stderr
                err = process.stderr.readline()
                if err:
                    errors.append(err)
                    self.debug_print(f"Error: {err.strip()}")
                
                # Check if process has finished
                if process.poll() is not None:
                    # Get any remaining output
                    for line in process.stdout:
                        output.append(line)
                        self.debug_print(f"Output: {line.strip()}")
                    for err in process.stderr:
                        errors.append(err)
                        self.debug_print(f"Error: {err.strip()}")
                    break
            
            stdout = ''.join(output)
            stderr = ''.join(errors)
            
            # Add results to markdown file
            with open(self.temp_md_file, 'a') as f:
                f.write(f"\n## Test Results: {script_name}\n")
                if fps_values:
                    avg_fps = sum(fps_values) / len(fps_values)
                    f.write(f"\n### Performance\n")
                    f.write(f"- Average FPS: {avg_fps:.2f}\n")
                    f.write(f"- Individual FPS measurements: {', '.join(f'{fps:.2f}' for fps in fps_values)}\n")
                
                f.write("\n### Raw Output\n```\n")
                f.write(stdout)
                f.write("```\n")
                
                if stderr:
                    f.write("\n### Errors/Warnings\n```\n")
                    f.write(stderr)
                    f.write("```\n")
            
            if stderr and "Traceback" in stderr:
                self.debug_print("\nFull error traceback:")
                self.debug_print(stderr)
                return False
            return True
            
        except Exception as e:
            self.debug_print(f"Test failed: {str(e)}")
            self.debug_print(traceback.format_exc())
            return False

    def run_all_tests(self):
        """Run all test configurations based on platform"""
        print("Starting tests...")
        
        try:
            success = True
            
            # Test 1: Basic MobileNet (works on all platforms)
            print("\nRunning basic MobileNet test...")
            if not self.run_test('Codes/mobile_net.py'):
                success = False
            
            # Test 2: Post-training quantization test
            print("\nRunning post-training quantization test...")
            if not self.run_quantization_test():
                success = False
            
            # Only run real-time quantized tests on Raspberry Pi
            if getattr(self, 'is_raspberry_pi', False):
                print("\nRunning real-time quantized MobileNet test...")
                if not self.run_test('Codes/mobile_net_quantized.py'):
                    success = False
                
                print("\nRunning real-time quantized MobileNet with predictions...")
                if not self.run_test('Codes/mobile_net_quantized_predictions.py'):
                    success = False
            
            if success:
                if os.path.exists(self.temp_md_file):
                    os.replace(self.temp_md_file, self.output_md_file)
                print(f"\nTests completed successfully. Results saved to {self.output_md_file}")
            else:
                print("\nSome tests failed. Check the output for details.")
                if os.path.exists(self.temp_md_file):
                    os.remove(self.temp_md_file)
                
        except Exception as e:
            print(f"\nError during test execution: {str(e)}")
            if os.path.exists(self.temp_md_file):
                os.remove(self.temp_md_file)

    def run_quantization_test(self):
        """Run post-training quantization demonstration"""
        try:
            print("\nDemonstrating post-training quantization...")
            
            # Load pre-trained model
            model = mobilenet_v2(pretrained=True)
            model.eval()
            
            # Create sample input
            input_tensor = torch.randn(1, 3, 224, 224)
            
            # Measure original model size and speed
            orig_size = os.path.getsize("temp_model.pth") if torch.save(model.state_dict(), "temp_model.pth") else 0
            
            start_time = time.time()
            with torch.no_grad():
                for _ in range(10):
                    model(input_tensor)
            orig_inference_time = (time.time() - start_time) / 10
            
            # Quantize model
            quantized_model = torch.quantization.quantize_dynamic(
                model,
                {torch.nn.Linear, torch.nn.Conv2d},
                dtype=torch.qint8
            )
            
            # Measure quantized model size and speed
            quant_size = os.path.getsize("temp_model_quant.pth") if torch.save(quantized_model.state_dict(), "temp_model_quant.pth") else 0
            
            start_time = time.time()
            with torch.no_grad():
                for _ in range(10):
                    quantized_model(input_tensor)
            quant_inference_time = (time.time() - start_time) / 10
            
            # Clean up temporary files
            if os.path.exists("temp_model.pth"):
                os.remove("temp_model.pth")
            if os.path.exists("temp_model_quant.pth"):
                os.remove("temp_model_quant.pth")
            
            # Add results to markdown
            with open(self.temp_md_file, 'a') as f:
                f.write("\n## Post-Training Quantization Results\n")
                f.write("\n### Model Size Comparison\n")
                f.write(f"- Original Model Size: {orig_size / 1024:.2f} KB\n")
                f.write(f"- Quantized Model Size: {quant_size / 1024:.2f} KB\n")
                f.write(f"- Size Reduction: {(1 - quant_size/orig_size) * 100:.2f}%\n")
                
                f.write("\n### Inference Speed Comparison\n")
                f.write(f"- Original Model Average Inference Time: {orig_inference_time * 1000:.2f} ms\n")
                f.write(f"- Quantized Model Average Inference Time: {quant_inference_time * 1000:.2f} ms\n")
                f.write(f"- Speed Improvement: {(1 - quant_inference_time/orig_inference_time) * 100:.2f}%\n")
            
            return True
            
        except Exception as e:
            print(f"Quantization test failed: {str(e)}")
            return False

if __name__ == "__main__":
    runner = LabRunner(output_md_file="lab_results.md")
    runner.run_all_tests() 
