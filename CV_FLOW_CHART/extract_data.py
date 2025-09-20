import pprint
import os
from slugify import slugify
import time


from config.log import logger

from detectConnectedComponents import detect_components
# from detectShapes import ShapeDetector
from detectShapesMultiThreaded import ShapeDetector
from detectLine import detect_lines_helper
from convert import convert_pdf_to_image
from getTextPDF import get_text_from_components
from OCR.strideOCR import ocrize_file_remote_server


'''
1. shape_id
2. shape_type
2. shape_text
3. shape_bbox
4. page_bbox
5. connected_comps(type:list) -  shape_id(id of other connected shapes), percentage_text
'''

def extract(file_path):
    start_time = time.time()
    
    input_file_name = os.path.basename(file_path)
    file_extension = file_path.split(".")[-1].lower()

    ocrized_pdf_output_name =  slugify(input_file_name).split('pdf')[0] + "_ocr.pdf"
    ocrized_pdf_output_path = os.path.join(os.path.dirname(file_path), ocrized_pdf_output_name)
    ocrized_pdf_path = ocrize_file_remote_server(file_path, ocrized_pdf_output_path)
    if file_extension =='pdf':
        image_path = convert_pdf_to_image(ocrized_pdf_path)
    else:
        image_path = file_path
    main_components, small_components, other_components = detect_components(image_path)
    
    
    sd = ShapeDetector()
    
    detect_shapes_start_time = time.time()
    detected_components = sd.detect_shapes_from_components(main_components, small_components)
    detect_shapes_end_time = time.time()
    logger.info("time taken for shape detection: {} sec".format(detect_shapes_end_time-detect_shapes_start_time))

    # detected_lines = detect_lines_helper(image_path, detected_components, other_components)
    detected_components = get_text_from_components(ocrized_pdf_path, detected_components, 1)
    detected_components.sort(key=lambda x: x["approx_rect"][1])
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(detected_components)
    end_time = time.time()
    logger.info("total time taken to process : {}".format(end_time-start_time))
    return detected_components


if __name__=="__main__":
    file_path = "/home/mohit/CV_FLOW_CHART/samples/OrgChart 1.pdf"
    # import cv2
    # img = cv2.imread(file_path)
    
    
    # # Convert image to grayscale
    # gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    # # thresh = cv2.threshold(gray, 150, 255,cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    # # pdf_path = "/home/mohit/converted_OrgChart 2.pdf"
    # cv2.imwrite("image5-2_gray.png", gray)
    extract(file_path)