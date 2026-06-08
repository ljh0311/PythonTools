# INF2009 Edge Computing Labs

This repository contains three comprehensive lab modules for edge computing on Raspberry Pi devices:

1. **Deep Learning on Edge** - Running and optimizing deep learning models on edge devices
2. **Image Analytics** - Real-time image processing and feature extraction
3. **Video Analytics** - Advanced video processing and object detection

All labs are designed to run on Raspberry Pi with Raspbian OS and demonstrate various techniques for efficient edge computing.

---

## Quick Start - GUI Launcher

A consolidated GUI launcher is available to run all experiments easily:

### Windows
```bash
run_launcher.bat
```

### Linux/Mac
```bash
chmod +x run_launcher.sh
./run_launcher.sh
```

### Direct Python
```bash
python launcher.py
```

The launcher provides:
- **Tabbed interface** for each module (DL on Edge, Image Analytics, Video Analytics)
- **Experiment selection** with radio buttons for easy navigation
- **Real-time output** display for each experiment
- **Configurable options** (quantization, duration, screenshot capture)
- **Results viewer** to browse and generate reports
- **Progress indicators** and status updates

### Launcher Features

1. **Deep Learning on Edge Tab**
   - Run MobileNet experiments (basic, quantized, with predictions)
   - Toggle quantization on/off
   - Enable/disable real-time predictions
   - View FPS measurements and performance metrics

2. **Image Analytics Tab**
   - Run color segmentation, HOG features, face detection, facial landmarks
   - Configure experiment duration
   - Capture screenshots automatically
   - View experiment output in real-time

3. **Video Analytics Tab**
   - Run optical flow, hand landmarks, gesture recognition, object detection
   - Configure experiment duration
   - Capture screenshots automatically
   - Monitor experiment progress

4. **Results & Reports Tab**
   - View results from all modules
   - Generate combined lab reports
   - Open results folders
   - Browse experiment outputs

---

## Module 1: Deep Learning on Edge

**Real-time Inference of Deep Learning models on Edge Device**

**Objective:** By the end of this session, participants will understand

1. How to run a deep learning model on an edge device (aka raspberryPi)
2. How does quantization work and different quantization methods for deep learning models

---

**Prerequisites:**

1. Raspberry Pi with Raspbian OS installed.
2. MicroSD card (16GB or more recommended).
3. Web camera compatible with Raspberry Pi.
4. Internet connectivity (Wi-Fi or Ethernet).
5. Basic knowledge of Python and Linux commands.

---

**1. Introduction**

Edge analytics with real-time processing capabilities is chellenging but important and inevitable due to privacy/security concerns. However, edge devices like RaspberryPi are constrained with limited hardware resources, which at times are not sufficient to run complex deep learning models. These models require lot of computational resource and memory due to their size and complex architecture. Therefore, in such scenarios, we optimize the model such that it can run efficiently with reduced inference time critical for real-time analytics. Optimization can be achieved by combination of techniques like quantization and converting trained model into architecture specific lite model.

**2. Running Deep Learning Model On RaspberryPi**

- **This section guide you on how to setup a Raspberry Pi for running PyTorch and deploy a MobileNet v2 image classification model in real time on the CPU.**

- Set up and activate a virtual environment named "dlonedge" for this experiment (to avoid conflicts in libraries) as below:

  ```bash
  sudo apt install python3-venv
  python3 -m venv dlonedge
  source dlonedge/bin/activate
  ```

- Installing PyTorch and OpenCV:

  ```bash
  pip install torch torchvision torchaudio
  pip install opencv-python
  pip install numpy --upgrade
  ```

- Same as last lab, for video capture we're going to be using OpenCV to stream the video frames. The model we are going to use in this lab is MobileNetV2, which takes in image sizes of 224x224. We are targeting 30fps for the model but we will request a slightly higher framerate of 36 fps than that so there is always enough frames and bandwidth of image pre-processing and model prediction.

- **Part 1.** [sample code](Codes/mobile_net.py) is used to directly load pre-trained MobileNetV2 model, doing model inference and finally, Observe the fps as shown in screenshot below when run on RaspberryPi 4B. As shown, with no optimization of model, we could only achieve of 5-6 fps much below our desired target.

  ![image1](https://github.com/user-attachments/assets/8e3cf302-45f3-41c9-85a5-a1bd118d30c4)

- **Part 2.** Edit line number 11 as shown below to enable quantization in [sample code](Codes/mobile_net.py) to use quantized version of MobileNetV2 model.

  ```bash
  quantize = True
  ```

    Finally, observe the fps as shown in screenshot below after using quantized model of MobileNetV2. We can now achieve close to 30 fps as required because of smaller footprint of quantized model.

    ![image2](https://github.com/user-attachments/assets/7086f300-4edf-4c41-a799-c496001ee1d1)

    [Quantization](https://pytorch.org/docs/stable/quantization.html) techniques enable computations and tensor storage at reduced bitwidths compared to floating-point precision. In a quantized model, some or all operations use this lower precision, resulting in a smaller model size and the ability to leverage hardware-accelerated vector operations.

- **Part 3.** Uncomment lines 57-61 in [sample code](Codes/mobile_net.py) to print the top 10 predictions in real-time as shown in below video.

<https://github.com/user-attachments/assets/5ee2a4c8-1988-4021-b194-aa0786a1ebfc>

**3. Quantization using Pytorch**

- Neural networks typically use 32-bit floating point precision for activations, weights, and computations. Quantization reduces this precision to smaller data types (like 8-bit integers), decreasing memory and speeding up computation. This compression is not lossless, as lower precision sacrifices dynamic range and resolution. Thus, a balance must be struck between model accuracy and the efficiency gains from quantization.

- In this section, we would learn how to use Pytorch to perform different quantization methods on a neural network architecture. There are two ways in general to quantize a deep learning model:

    1. Post Training Quantization: After we have a trained model, we can convert the model to a quantized model by converting 32 bit floating point weights and activations to 8 bit integer, but we may see some accuracy loss for some types of models.
    2. Quantization Aware Training: During training, we insert fake quantization operators into the model to simulate the quantization behavior and convert the model to a quantized model after training based on the model with fake quantize operators. This is harder to apply than post-training quantization since it requires retraining the model, but typically gives better accuracy.

- Please refer to [sample jupyter notebook file](Codes/PyTorch_Quantisation.ipynb), which demonstrates how to quantized a pre-trained model using post-training quantization approach as well as quantization aware training. Please run the sample code preferably in google colab if you do not have computer with good hardware specs.

**4. Homework and Optional Exercise**

- Try running quantized version of some large language models (like llama, mixtral etc.) on Raspberry Pi. This [link](https://www.dfrobot.com/blog-13498.html) demonstrates some of the LLMs on Raspberry Pi 4 and 5.
- Take any complex Deep Learning Model like resnet, mobileNet OR your own architecure and try different quantization methods as explained in section 3. Once deployed on RaspberryPi, Observe the size, performance and speed of the quantized model.

---

## Module 2: Image Analytics

**Image Analytics with Raspberry Pi using Web Camera**

**Objective:** By the end of this session, participants will understand how to set up a web camera with the Raspberry Pi, capture images, and perform basic and advanced image analytics.

---

**Prerequisites:**

1. Raspberry Pi with Raspbian OS installed.
2. MicroSD card (16GB or more recommended).
3. Web camera compatible with Raspberry Pi (Will be using USB Webcam for this experiment).
4. Internet connectivity (Wi-Fi).
5. Basic knowledge of Python and Linux commands.

---

**1. Introduction (10 minutes)**
Computer vision has been a very popular field since the advent of digital systems. However computer vision on the edge devices such as Raspberry Pi is challenging due to resource contraints. Edge Computer Vision (ECV) has emerged as a transformative technology, with [Gartner](https://www.linkedin.com/pulse/what-edge-computer-vision-how-get-started-deep-block-net) recognizing it as one of the top emerging technologies of 2023. ECV offers several benefits such as 1) they can operate in real-time or near-real-time, providing instant insights and enabling immediate actions, 2) they offer enhanced privacy and security and 3) It reduces dependency on network connectivity or relaxes the bandwidth requirements as some processing will be done within.
In this lab, few basic and advanced image processing tasks on edge devices is introduced. An overview of the experiments/setup is as follows:
![image](https://github.com/drfuzzi/INF2009_VideoAnalytics/assets/52023898/882c84dc-1989-4039-807d-554a079e3776)

**2. Setting up the Raspberry Pi (15 minutes)**

- Booting up the Raspberry Pi.
- Setting up Wi-Fi/Ethernet.
- System updates:

  ```bash
  sudo apt update
  sudo apt upgrade
  ```

- **[Important!] Set up and activate a virtual environment named "image" for this experiment (to avoid conflicts in libraries) as below**

  ```bash
  sudo apt install python3-venv
  python3 -m venv image
  source image/bin/activate

**3. Connecting and Testing the Web Camera (5 minutes)**

- Physically connect the web camera to the Raspberry Pi.
  
**. Introduction to Real-time Image Processing with Python (25 minutes)**

- Installing OpenCV:

  ```bash
  pip install opencv-python  
  ```

- The [sample code](Codes/image_capture_display.py) shows the code to read frames from a webcam and then based on the intensity range for each colour channel (RGB), how to segment the image into red green and blue images. A sample image and the colour segmentation is as shown below:
  ![image](https://github.com/drfuzzi/INF2009_ImageAnalytics/assets/52023898/fd7c115d-0301-0d2-b2c1-7966dce3fec)
- Expand the code to segment another colour (say yellow)

**5. Real-time Image Analysis (25 minutes)**

- Installing scikit-image:

  ```bash
  pip install scikit-image  
  ```

- Computer vision employs feature extraction from images. Some important image features include edges and textures. In this section we will employ a feature named histogram of gradients (HoG) which is widely employed for face recognition and other tasks. HoG involves gradient operation (basically extracting edges) on various image patches (by dividing the image into blocks). A [sample code](Codes/image_hog_feature.py) involving scikit-image is employed for the same. The code displays the dominant HoG image for each image patch overlaid on the actual image. It has to be noted that OpenCV can also be employed for the same task, but the visualization using scikit-image is better compared to that from OpenCV. A sample image for the HoG feature is as shown below:
![image](https://github.com/drfuzzi/INF2009_ImageAnalytics/assets/52023898/94e7d597-c259-4634-a3dc-437c79e8533b)
  - Note the usage of colour (RGB) to gray scale converion employed before HoG feature extraction.
  - Run the code with and without resizing the image and observe the resultant frame rate. It is important to note that for edge computing, downsizing the image will speed up the compute and many such informed decisions are critical.
  - Change the patch size in line 25 (feature.hog) and observe the changes in the results.
- The HoG features can be employed to identify the presence of face. An [example using OpenCV](Codes/image_human_capture.py) is available for experimenting with. A multiscale HoG feature extraction is employed in this case. This involves extracting HoG features at multiple scales (resolutions) of the given image.

**6. Real-time Image Feature Analysis for Face Capture and Facial Landmark Extraction (20 minutes)**

- In this work, a light weight opensource library named *"Mediapipe"* for tasks such as face landmark detection, pose estimation, hand landmark detection, hand gesture recognition and object detection using pretrained neural network models.
- [MediaPipe](https://developers.google.com/mediapipe) is a on-device (*embedded machine learning*) framework for building cross platform multimodal applied ML pipelines that consist of fast ML inference, classic computer vision, and media processing (e.g. video decoding). MediaPipe was open sourced at CVPR in June 2019 as v0.5.0 and has various lightweight models developed with Tensorflow lite available for usage.
- Installing media pipe:

  ```bash  
  pip install mediapipe
  ```

- Try the [sample code](Codes/image_face_capture.py) to detect the face based on Mediapipe's approach which is very light weight when compared to the approach employed in above section. Observe the speed up. - A sample image with face landmarks is as shown below:
![Mediapipe Face Mesh_screenshot_18 01 2025](https://github.com/user-attachments/assets/3e952cbb-72df-4258-9d96-83f05c741096)

- [Optional] An opencv alternative (no dependence on mediapipe) of the face detection is available in the [sample code](Codes/image_human_capture_opencv.py). If you are using this code, make sure you download the [Haar cascade model](https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_alt2.xml) manually and save it as 'haarcascade_frontalface_alt2.xml' in the same folder as the code.

---

**[Optional] Homework/Extended Activities:**

1. Explore more advanced OpenCV functionalities like SIFT, SURF, and ORB for feature detection. These features alongside HoG could be used for image matching (e.g. face recognition)
2. Build an eye blink detection system for drowsiness detection.  

---

**Resources:**

1. Raspberry Pi official documentation.
2. OpenCV documentation and tutorials.
3. Relevant Python libraries documentation for image processing (e.g., `opencv`, `scikit-image`, `mediapipe`).

---

## Module 3: Video Analytics

**Video Analytics with Raspberry Pi using Web Camera**

**Objective:** By the end of this session, participants will understand how to set up a web camera with the Raspberry Pi, capture video streams, and perform basic and advanced video analytics.

---

**Prerequisites:**

1. Raspberry Pi with Raspbian OS installed.
2. MicroSD card (16GB or more recommended).
3. Web camera compatible with Raspberry Pi.
4. Internet connectivity (Wi-Fi or Ethernet).
5. Basic knowledge of Python and Linux commands.

---

**1. Introduction (10 minutes)**

- Video analytics is an emerging field employed to extract valuable insights from video data. Edge video analytics with real-time processing capabilities is chellenging but important and inevitable due to privacy/security concerns. Also, in many cases redundancy can be avoided to save on the bandwidth requirements (e.g. compress the video to have only key (important) frames). In this lab, few basic and advanced video processing tasks on edge devices is introduced. An overview of the experiments/setup is as follows:
![image](https://github.com/drfuzzi/INF2009_VideoAnalytics/assets/52023898/882c84dc-1989-4039-807d-554a079e3776)

**2. Setting up the Raspberry Pi (10 minutes)**

- Booting up the Raspberry Pi.
- Setting up Wi-Fi/Ethernet.
- System updates:

  ```bash
  sudo apt update
  sudo apt upgrade
  ```

**3. Connecting and Testing the Web Camera (5 minutes)**

- Please ensure the web camera is working and proceed to subsequent steps.

**4. Introduction to real-time video processing on raspberry pi (20 minutes)**

- **[Important!] Set up and activate a virtual environment named "video" for this experiment (to avoid conflicts in libraries) as below. You can also reuse the virtual environment "image" as we are employing opencv and mediapipe libraries for video analytics**

  ```bash
  sudo apt install python3-venv
  python3 -m venv video
  source video/bin/activate
- Installing OpenCV:

  ```bash
  pip install opencv-python  
  ```

- [Optical flow](https://en.wikipedia.org/wiki/Optical_flow) estimation is employed to track moving objects in a video sequence. In this section, we will employ the purely opencv based [sample code](Codes/optical_flow.py) for estimaging the flow using Lucas Kanade Optical Flow approach and Flow Farneback approach. The displays are in the form of streamlines or directional arrows as shown below. \
  ![image](https://github.com/drfuzzi/INF2009_VideoAnalytics/assets/52023898/c5987191-27ff-44f9-ac85-d1a673477dc8)
  ![image](https://github.com/drfuzzi/INF2009_VideoAnalytics/assets/52023898/f9a6d18e-4973-44f9-80f5-ac01d090cc1)
  - **[Important]** You need to comment/uncomment respective lines (line 119/121) to activate the desired results. Modify the parameters (line 12/18) by looking into the OpenCV documentation and observe/note down the observations/conclusions.

**5. Advanced Video Analytics (40 minutes)**

- We will employ a light weight opensource library named *"Mediapipe"* for tasks such as face landmark detection, pose estimation, hand landmark detection, hand gesture recognition and object detection using pretrianed light weight models.
- [MediaPipe](https://developers.google.com/mediapipe) is a on-device (*embedded machine learning*) framework for building cross platform multimodal applied ML pipelines that consist of fast ML inference, classic computer vision, and media processing (e.g. video decoding). MediaPipe was open sourced at CVPR in June 2019 as v0.5.0 and has various lightweight models developed with Tensorflow lite available for usage.
- Installing media pipe:

  ```bash  
  pip install mediapipe
  ```

- Hand landmark detection
  - Download the handlandmark detection model:

    ```bash
    wget -q https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
    ```

  - The [sample code](Codes/hand_landmark.py) employs opencv and mediapipe to detect the human hand and subsequently the finger locations (the tip of thumb and index finger as well as a simple logic to predict if the thumb is pointing up) based on the [finger model](https://developers.google.com/mediapipe/solutions/vision/hand_landmarker) outlined below :
    ![image](https://github.com/drfuzzi/INF2009_VideoAnalytics/assets/52023898/1090e213-7a56-4059-9386-50123bd6f8f8)
  - Modify the code to show all the 21 finger points and observe the same while moving the hand.
  - Modify the code to predict the number of fingers and display the same overlaid on the image as text (e.g. if four fingers are raised, display '4' on the screen and if three fingers on one hand and two on the other, the display should be '5').

**6. Advanced Video Analytics (20 minutes)**

- In this section, we will work on more advanced analytics tasks such as hand gesture recognition and object detection based on pretrianed light weight models.
- Hand gesture recognition
  - Download the hand gesture recognition model:

    ```bash
     wget -O gesture_recognizer.task -q https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task
    ```

  - The [sample code](Codes/hand_gesture.py) shows a real-time hand gesture recongition task. A sample snapshot of the code result for victory sign is shown below: \
    ![image](https://github.com/drfuzzi/INF2009_VideoAnalytics/assets/52023898/84bf1517-22c0-427a-9ca7-047551f1b50e)
- Object detection
  - Download the light weight EfficientDet object detection model:

    ```bash
     wget -q -O efficientdet.tflite -q https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/int8/1/efficientdet_lite0.tflite
    ```

  - The [sample code](Codes/obj_detection.py) shows a real-time object detection task.
  - Based on the above code, write a code to do object detection based video summarization (e.g. for a video with only frames having a cellphone)

---

**[Optional] Homework/Extended Activities:**

1. Experiment with more advanced tracking algorithms available in OpenCV.
2. Build a gesture based video player control (e.g. could use libraries like [Pyautogui](https://pyautogui.readthedocs.io/en/latest/) for the same)
3. Build a surveillance system based on video based motion detection.

---

**Resources:**

1. Raspberry Pi official documentation.
2. OpenCV documentation and tutorials.
3. Mediapipe documentation and tutorials.

---
