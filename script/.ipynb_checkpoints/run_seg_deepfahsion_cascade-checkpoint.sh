
GPU_NUM=0  
DATA_NAME="Deepfashion"
MODEL_NAME="cascade_mask_rcnn"
INPUT_PATH="./data/Deepfashion_dataset"
OUTPUT_PATH="./model"
MODEL_PATH="Misc/cascade_mask_rcnn_R_50_FPN_3x.yaml"
CONFIG_PATH="./src/configs.yaml"
PRETRAINED_PATH="Misc/cascade_mask_rcnn_R_50_FPN_3x.yaml"

    

# mask r-cnn
CUDA_VISIBLE_DEVICES=${GPU_NUM} python src/segment.py \
    --data_name ${DATA_NAME} \
    --model_name ${MODEL_NAME} \
    --input_path ${INPUT_PATH} \
    --output_path ${OUTPUT_PATH} \
    --model_path ${MODEL_PATH} \
    --config_path ${CONFIG_PATH} \
    --pretrained_path ${PRETRAINED_PATH} 


    

