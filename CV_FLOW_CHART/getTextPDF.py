import fitz
from bbox_helper import get_words_from_bbox_pymu
from config.log import logger

def get_text_from_components(pdf_path, detected_components, page_num):
    text = None
    final_components = []
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num-1]
        page_height = page.rect[3]
        page_width = page.rect[2]

        # drawn box
        # bottom-left
        # height - y
        # x0, y2, x1, y0

        
        pymu_dict = page.get_text("rawdict")
        sorted_pymu = sorted(pymu_dict["blocks"], key=lambda x: (x["bbox"][3], x["bbox"][0]))
        all_words = []
        for block_object in sorted_pymu:
            if block_object["type"] ==1:
                continue
            lines = block_object.get("lines",[])
            
            
            for line in lines:
                spans = line["spans"]
                for span in spans:
                    for char_word in span["chars"]:
                        all_words.append(char_word)

        # calculate average charcter length to give padding to drawn bbox by user 
        # char_y_lens = [abs(ch["bbox"][3] - ch["bbox"][1]) for ch in all_words]
        # avg_char_len = mode(char_y_lens)


        # padding
        padding = 0
        for component in detected_components:
            try:
                drawn_bbox = component["approx_rect"]
                drawn_bbox = [drawn_bbox[0]*page_width, drawn_bbox[1]*page_height, drawn_bbox[2]*page_width, drawn_bbox[3]*page_height]
                matched_words, text = get_words_from_bbox_pymu(drawn_bbox, all_words)
                text = text.strip()
                if text!="":
                    component["text"] = text
                    final_components.append(component)

                # print(text)
            except Exception as e:
                logger.info("error in extracting component {} with e:{}".format(component, e))


    except Exception as e:
        logger.info("error in extracting text from bbox function with {}".format(e))
    return final_components