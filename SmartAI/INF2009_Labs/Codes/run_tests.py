import subprocess
import time
from datetime import datetime
import os


def run_test(script_name, output_file):
    """Run a test script and capture its output"""
    print(f"\nRunning {script_name}...")

    # Run the script and capture output
    try:
        result = subprocess.run(
            ["python3", script_name], capture_output=True, text=True, timeout=60
        )  # 60 second timeout

        # Write output to file
        with open(output_file, "a") as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"Test: {script_name}\n")
            f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*50}\n\n")

            # Write stdout
            f.write("Output:\n")
            f.write(result.stdout)

            # Write stderr (usually contains warnings)
            if result.stderr:
                f.write("\nWarnings/Errors:\n")
                f.write(result.stderr)

            f.write(f"\n{'='*50}\n")

        # Extract FPS measurements
        fps_values = []
        for line in result.stdout.split("\n"):
            if "fps" in line.lower():
                try:
                    fps = float(line.split("=")[1].strip(" fps="))
                    fps_values.append(fps)
                except:
                    pass

        # Calculate average FPS
        if fps_values:
            avg_fps = sum(fps_values) / len(fps_values)
            with open(output_file, "a") as f:
                f.write(f"\nAverage FPS: {avg_fps:.2f}\n")

        return True
    except subprocess.TimeoutExpired:
        with open(output_file, "a") as f:
            f.write(f"\nError: Test timed out after 60 seconds\n")
        return False
    except Exception as e:
        with open(output_file, "a") as f:
            f.write(f"\nError: {str(e)}\n")
        return False


def main():
    # Create results directory if it doesn't exist
    if not os.path.exists("results"):
        os.makedirs("results")

    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"results/test_results_{timestamp}.txt"

    # Write system info
    with open(output_file, "w") as f:
        f.write("Deep Learning on Edge - Test Results\n")
        f.write(f"Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Get system info
        try:
            # Get Raspberry Pi model
            with open("/proc/device-tree/model", "r") as model:
                f.write(f"Device: {model.read().strip()}\n")
        except:
            f.write("Device: Unknown\n")

        # Get Python version
        python_version = (
            subprocess.check_output(["python3", "--version"]).decode().strip()
        )
        f.write(f"Python: {python_version}\n")

        # Get pip packages
        f.write("\nInstalled Packages:\n")
        pip_list = subprocess.check_output(["pip3", "list"]).decode()
        f.write(pip_list)
        f.write("\n")

    # Run each test
    tests = [
        "mobile_net_basic.py",
        "mobile_net_quantized.py",
        "mobile_net_quantized_predictions.py",
    ]

    for test in tests:
        run_test(test, output_file)

    print(f"\nAll tests completed. Results saved to {output_file}")


if __name__ == "__main__":
    main()
