import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_DIR = os.getcwd()

PDF_PATH = os.path.join(BASE_DIR, 'pdf_documents')
if not os.path.exists(PDF_PATH):
    os.makedirs(PDF_PATH)

SCAN_PDFS = os.path.join(PDF_PATH, 'scanned')
if not os.path.exists(SCAN_PDFS):
    os.makedirs(SCAN_PDFS)

CONF = os.path.join(BASE_DIR, 'config')

# gfo signature
PDF_TO_IMG_PATH = os.path.join(PDF_PATH, 'img_pdf')

# gfo configs
MASTER_JSON = os.path.join(CONF, 'gfo_config')
ALIAS_PATH = os.path.join(MASTER_JSON, 'alias_key.json')
ALL_COUNTRY_SWIFT_CODE = os.path.join(MASTER_JSON, 'all_country_bic.json')
DATA_LABELS = os.path.join(MASTER_JSON, 'datapoints_name.json')
MASTER_TABLE_JSON = os.path.join(MASTER_JSON, 'master_table_v3.json')
REGEX_PATH = os.path.join(MASTER_JSON, 'regex.json')
TRAIN_DATA_PATH = os.path.join(MASTER_JSON, 'gfo_train_data.csv')

# gfo models path
MODELS = os.path.join(CONF, 'gfo_ner_models')
MODEL_7_ENTITY_PATH = os.path.join(MODELS, 'new_new_set_2_10_ent') 
MODEL_9_ENTITY_PATH = os.path.join(MODELS, 'new_v3_set_1_10_ent')

MODEL_PATH = os.path.join(CONF, 'table_dl_model/model_196000.pth')
CASCADE_MODEL_PATH = os.path.join(CONF, 'table_dl_model/epoch_v2.pth')
CASCADE_MASK = os.path.join(BASE_DIR, 'common/cascade_table_helper/cascade_mask_rcnn_hrnetv2p_w32_20e_v2.py')


# 10k config
SECK_MASTER = os.path.join(CONF, "10k_config")
SECK_DATA_LABELS = os.path.join(SECK_MASTER, 'datapoints.json')