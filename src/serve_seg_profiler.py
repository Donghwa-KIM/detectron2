import argparse
import yaml
import os
import logging
import matplotlib.pyplot as plt
import pytz

from detectron2.data import MetadataCatalog, DatasetCatalog
from detectron2.config import get_cfg
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.evaluation import COCOEvaluator, inference_on_dataset
from detectron2.data import build_detection_test_loader
from detectron2.utils.visualizer import Visualizer
from detectron2.utils.visualizer import ColorMode
from time import gmtime, strftime
from datetime import datetime
from time import time
from utils import *
import psutil

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


class FailException:
    def __init__(self, json_path, func2failnum):
        self.json_path = json_path
        self.func2failnum = func2failnum
        
    def __call__(self, func):
        def inner_function(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                e.args = (f'{self.func2failnum[func.__name__]} in {func.__name__} => ' + e.args[0] ,)
                result_print = save_json(self.json_path, self.func2failnum[func.__name__],{})
                print("ERROR CODE :", 103)
                print(e)
                print(result_print)
                exit()
                raise 

        return inner_function
    
def load_model_configs(args):
    with open(args.config_path) as f:
        configs = yaml.load(f, Loader=yaml.FullLoader)
    return configs

    
def cv2_imshow(a, **kwargs):
    a = a.clip(0, 255).astype('uint8')
    # cv2 stores colors as BGR; convert to RGB
    if a.ndim == 3:
        if a.shape[2] == 4:
            a = cv2.cvtColor(a, cv2.COLOR_BGRA2RGBA)
        else:
            a = cv2.cvtColor(a, cv2.COLOR_BGR2RGB)

    return plt.imshow(a, **kwargs)


def get_checkpoint(args):    
    # best model search
    experiment_folder = os.path.join(args.model_weights)
    model_idx = get_best_checkpoint(experiment_folder)
    return model_idx


def build_categories(configs):
    MetadataCatalog.get('inference').set(thing_classes = configs['Detectron2']['LABEL_LIST']['kfashion'])
    fashion_metadata = MetadataCatalog.get('inference')
    return fashion_metadata


def get_labels(configs, outputs):
    return np.array(configs['Detectron2']['LABEL_LIST']['kfashion'])[
        outputs['instances'].pred_classes.detach().cpu().numpy()].tolist()


def get_image(args):
    return cv2.imread(args.image_path)


def get_predictor(args, configs):
    # model build and load
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file(args.model_path))
    cfg.DATASETS.TRAIN = ()
    cfg.DATASETS.TEST = () 
    cfg.DATALOADER.NUM_WORKERS = configs['Detectron2']['DATALOADER_NUM_WORKERS'] # cpu
    cfg.SOLVER.IMS_PER_BATCH = configs['Detectron2']['SOLVER_IMS_PER_BATCH'] # allocation t
    cfg.MODEL.DEVICE = 'cpu'
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = configs['Detectron2']['MODEL_ROI_HEADS_BATCH_SIZE_PER_IMAGE']  # number of items in batch update
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(configs['Detectron2']['LABEL_LIST']['kfashion'])  # num classes
    cfg.MODEL.WEIGHTS = os.path.join(args.model_weights,f"model_{args.model_idx.zfill(7)}.pth")
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5   # set a custom testing threshold

    predictor = DefaultPredictor(cfg)
    
    return predictor


def save_json(path, code, body):
    tz_kor = pytz.timezone('Asia/Seoul') 
    json_dict = {}
    
    json_dict["resultCode"] = code
    json_dict["resultMessage"] = "SUCCESS" 
    json_dict["body"] = body
    json_dict["responseDate"] = datetime.now(tz_kor).strftime('%Y-%m-%d %H:%M:%S')
    
    with open(path, "w") as f:
        json.dump(json_dict, f)
        logger.info("Saved json in {}".format(path))
    return json_dict


def plot(args, fashion_metadata, im, outputs, labels):
    plt.figure(figsize=(7,7))
    v = Visualizer(im[:, :, ::-1],
                   metadata=fashion_metadata, 
                   scale=0.5, 
                   instance_mode=ColorMode.IMAGE_BW   # remove the colors of unsegmented pixels. This option is only available for segmentation models
    )
    out = v.draw_instance_predictions(outputs["instances"].to("cpu"))

    cv2_imshow(out.get_image()[:, :, ::-1])
    plt.axis('off')

    plt.savefig(os.path.join(args.save_path,'images', f"{os.path.basename(args.image_path)}"),bbox_inches='tight')
    logger.info("Saved image in {}".format(os.path.join(args.save_path, 'images', f"{os.path.basename(args.image_path)}")))
    plt.close()


if __name__ == "__main__":
    pid = os.getpid()
    py = psutil.Process(pid)

    print("Starting...")
    t1 = time()
    default_path = os.path.join("/home/korea", "fashion-recommendation")
    # print(os.getcwd())
    if os.getcwd() != default_path:
        os.chdir(default_path)
        print("path >>>", os.getcwd())
    try:
        print("[1/6] parser_args.")
        parser = argparse.ArgumentParser()
        parser.add_argument("--image_path", type=str, default="./dataset/samples/056665.jpg", help='input image')
        parser.add_argument("--save_path", type=str, default="./dataset/seg_images", help='save root')
        parser.add_argument("--model_weights", type=str, default="./model/kfashion_cascade_mask_rcnn", help='model checkpoints')
        parser.add_argument("--model_path", type=str, default="Misc/cascade_mask_rcnn_R_101_FPN_3x.yaml", help='--pretrained COCO dataset for semgentation task')
        parser.add_argument("--config_path", type=str, default="./src/configs.yaml", help='-- convenient configs for models')
        args = parser.parse_args()
    except Exception as ex:
        print("ERROR CODE :", 101)
        print(ex)
        exit()

    print(py.cpu_percent() / psutil.cpu_count())
    print(py.memory_full_info().rss / 1024 / 1024)
    # model configs
    try:
        print("[2/6] load_model_configs.")
        configs = load_model_configs(args)
    except Exception as ex:
        print("ERROR CODE :", 102)
        print(ex)
        exit()

    print(py.cpu_percent() / psutil.cpu_count())
    print(py.memory_full_info().rss / 1024 / 1024)
    print("[3/6] set fail_exception.")
    # set fail_exception
    json_path = os.path.join(args.save_path, 'jsons', f"{os.path.basename(args.image_path).split('.')[0]}.json")
    fail_exception = FailException(json_path, configs['exception']['seg'])

    @fail_exception
    def check_image(im):
        if im is None:
            raise Exception('Can not load the image, check the image path!')

    @fail_exception        
    def check_num_labels(labels):
        if len(labels)==0:
            raise Exception('Nothing to be predicted for the image')

    print(py.cpu_percent() / psutil.cpu_count())
    print(py.memory_full_info().rss / 1024 / 1024)
    try:
        print("[4/6] build_categories.")
        # categoies info
        fashion_metadata = build_categories(configs)
        # model index
        args.model_idx = get_checkpoint(args)
        # save path
        os.makedirs(os.path.join(args.save_path,'images'), exist_ok =True)
        os.makedirs(os.path.join(args.save_path,'jsons'), exist_ok =True)
    except Exception as ex:
        print("ERROR CODE :", 104)
        print(ex)
        exit()

    print(py.cpu_percent() / psutil.cpu_count())
    print(py.memory_full_info().rss / 1024 / 1024)
    try:
        print("[5/6] prediction.")
        # model for semgmentation
        predictor = get_predictor(args, configs)
        logger.info(f"Extracting for {args.image_path}")
        # get image
        im = get_image(args)
        check_image(im)
        # prediction
        outputs = predictor(im)
        labels = get_labels(configs, outputs)
        check_num_labels(labels)
        logger.info(f"Extracted {len(labels)} items")
        # save the segmented image
        plot(args, fashion_metadata, im, outputs, labels)
    except Exception as ex:
        print("ERROR CODE :", 105)
        print(ex)
        exit()

    print(py.cpu_percent() / psutil.cpu_count())
    print(py.memory_full_info().rss / 1024 / 1024)
    try:
        print("[6/6] save json.")
        # save json
        # server_root = os.path.join("/home/korea/fashion-recommendation/","/".join(args.save_path.split('/')[1:]))
        server_root = args.save_path
        img_path = os.path.abspath(os.path.join(server_root, 'images', f"{os.path.basename(args.image_path)}"))
        result_print = save_json(json_path, "SUCCESS", {"filePath": img_path})
        print("[DONE] Total time spent : {:.4f} seconds.".format(time()-t1))
        print(result_print)
    except Exception as ex:
        print("ERROR CODE :", 106)
        print(ex)
        exit()
