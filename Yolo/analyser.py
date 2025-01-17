def warn(*args, **kwargs):
    pass
import warnings
warnings.warn = warn


from torchvision import datasets, transforms
from torch.utils.data import DataLoader
import os, sys, time, datetime, random
from torch.autograd import Variable
from collections import deque
from PIL import Image
from models import *
from utils import *
import torch
import json
import cv2

# load weights and set defaults
config_path='config/yolov3.cfg'
weights_path='config/yolov3.weights'
class_path='config/coco.names'
img_size=416
conf_thres=0.8
nms_thres=0.4


# load model and put into eval mode
model = Darknet(config_path, img_size=img_size)
model.load_weights(weights_path)
model.cpu()
model.eval()
color = (255,0,0)
classes = utils.load_classes(class_path)
Tensor = torch.FloatTensor

class DataLoaderSettings():
    pass


# Get detected instances of classes
def detect_image(img, classList):
    # scale and pad image
    ratio = min(img_size/img.size[0], img_size/img.size[1])
    imw = round(img.size[0] * ratio)
    imh = round(img.size[1] * ratio)
    img_transforms = transforms.Compose([ transforms.Resize((imh, imw)),
         transforms.Pad((max(int((imh-imw)/2),0), max(int((imw-imh)/2),0), max(int((imh-imw)/2),0), max(int((imw-imh)/2),0)),
                        (128,128,128)),
         transforms.ToTensor(),
         ])
    # convert image to Tensor
    image_tensor = img_transforms(img).float()
    image_tensor = image_tensor.unsqueeze_(0)
    input_img = Variable(image_tensor.type(Tensor))
    # run inference on the model and get detections
    with torch.no_grad():
        detections = model(input_img)
        detections = utils.non_max_suppression(detections, 80, conf_thres, nms_thres)
        
        realDetections = []
        
        #remove unwanted classes
        if detections is not None:
            for d in detections:
                if d is not None:
                    className = classes[int(d[0].cpu()[6])]
                    if className in classList:
                        realDetections.append(d)
        
        if len(realDetections) > 0:
            return realDetections[0]

    return None

def get_image(opt=None, frame=None):
    if frame is not None:
        new_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pilimg = Image.fromarray(new_frame)
        return pilimg
    else:
        dataloader = DataLoader(
            ImageFolder(opt.image_folder, img_size=opt.img_size),
            batch_size=opt.batch_size,
            shuffle=False,
            num_workers=opt.n_cpu,
        )
        return dataloader

classlist = ["person"]
frameNum = 0
print(classlist)
print(classes[0])

vid = cv2.VideoCapture("./data/earthcam-1.mp4")

frames_to_drop = 15
current_frames = 0

while True:

    peoplecount = 0
        
    ret, frame = vid.read()
    if not ret:
        break

    if current_frames < frames_to_drop:
        current_frames += 1
        continue

    current_frames = 0

    frameNum += 1
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    pilimg = get_image(None, frame)
    detections = detect_image(pilimg, classlist)

    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    img = np.array(pilimg)
    pad_x = max(img.shape[0] - img.shape[1], 0) * (img_size / max(img.shape))
    pad_y = max(img.shape[1] - img.shape[0], 0) * (img_size / max(img.shape))
    unpad_h = img_size - pad_y
    unpad_w = img_size - pad_x

    if detections is not None:
        #detections = rescale_boxes(detections, img_size, img.shape[:2])

        for x1, y1, x2, y2, conf, cls_conf, cls_pred in detections:
            #get bounding box cordinates
            box_h = int(((y2 - y1) / unpad_h) * img.shape[0])
            box_w = int(((x2 - x1) / unpad_w) * img.shape[1])
            y1 = int(((y1 - pad_y // 2) / unpad_h) * img.shape[0])
            x1 = int(((x1 - pad_x // 2) / unpad_w) * img.shape[1])
            center = (round(x1 + (box_w / 2)), round(y1 + (box_h / 2)))
            cls = classes[int(cls_pred)]
            if cls in classlist:
                cv2.rectangle(frame, (x1, y1), (x1+box_w, y1+box_h), color, 4)
                cv2.rectangle(frame, (x1, y1-105), (x1+len(cls)*19+80, y1), color, -1)
                cv2.putText(frame, cls + "-" + str(int(cls_pred)), (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 3)

            pass

    scale_percent = 50 # percent of original size
    width = int(frame.shape[1] * scale_percent / 100)
    height = int(frame.shape[0] * scale_percent / 100)
    dim = (width, height)
    # resize image
    resized = cv2.resize(frame, dim, interpolation = cv2.INTER_AREA) 

    cv2.imshow('Stream', resized)
    ch = 0xFF & cv2.waitKey(1)
    if ch == 27:
        break

cv2.destroyAllWindows()
