# Repository for exploring existing CNN architectures in [torchvision models](https://pytorch.org/vision/stable/models.html), Fine tuning and transfer learning ImageNet models to classify birds in [CUB-200-2011 dataset](https://www.vision.caltech.edu/datasets/cub_200_2011/) and Explain models through feature visualization and understanding

The repository has three parts with homeworks for each part. All the parts are to be done in Google Colab and the reference notebooks are appended in the parts below.

# Part 1: Compare ImageNet Models

1. Download the ImageNet sample dataset and class list from the provided links and upload them to your Google Drive.
2. Open [compare_ImageNetModels.ipynb](compare_ImageNetModels.ipynb) in Google Colab.
3. Follow the instructions in the notebook and complete the exercise.

# Part 2: Transfer Learning with ResNet-50

1. Download the prepared CUB-200-2011 dataset from [this link](https://www.google.com/url?q=https%3A%2F%2Fdrive.google.com%2Ffile%2Fd%2F1pt1BcNDcJsEp7QLJgPqGLkuVXy5GeUPw%2Fview%3Fusp%3Dsharing) and upload it to Google Drive.
2. Open [transfer_learning.ipynb](transfer_learning.ipynb) in Google Colab.
3. Follow the notebook instructions to complete the assignment.

# Part 3: Model Explainability and Visualization

1. Make sure you've set up the dataset as in Part 2.
2. Open [model_explainability.ipynb](model_explainability.ipynb) in Colab.
3. Complete the tasks in the notebook to explore feature visualization and explainability methods like Grad-CAM and Saliency Maps.

# References

* [CUB-200-2011 dataset](https://www.vision.caltech.edu/datasets/cub_200_2011/)
* [ImageNetSamples](https://github.com/EliSchwartz/imagenet-sample-images)
* [Jacob Gil's pytorch-gradcam](https://jacobgil.github.io/pytorch-gradcam-book/introduction.html)
* [Ben Trevett's Pytroch Image Classification](https://github.com/bentrevett/pytorch-image-classification/tree/master)
* [Getting hooked with PyTorch and Grad-CAM](https://www.kaggle.com/code/noobiedatascientist/getting-hooked-with-pytorch-and-grad-cam)
