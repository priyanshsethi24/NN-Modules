import cv2

def get_words_from_bbox_pymu(bbox, words_in_doc, tolerance=0.2):
    '''
    Function to get words within a bbox drawn by end user

    Args:
        bbox (list) - bounding box coordinates of the bbox drawn by user
        words_in_doc (list of dict) - pymu words extracted from a doc
        tolerance (float) [0,1] - tolerance of coverage to check for matching words
    
    Returns:
        matching_words (list of dict) - words found in the bbox
        word (String) - text of the matching word
    '''

    matching_words = []

    
    for word in words_in_doc:
        ref_bbox = [word["bbox"][0], word["bbox"][1], word["bbox"][2] ,word["bbox"][3]]
        box_coverage = calc_coverage(ref_bbox,bbox)
        if box_coverage > tolerance:
            matching_words.append(word)
    

    def join_word(matching_words: list) -> list:
        '''
        Function to join pymu chars extarcted to get the derived text

        Args:
            matching_words (list of dict) - Matching chars found in the outer function
        
        Returns:
            (String) - text derived from the matching words
        '''

        derived_word = matching_words[0]["c"]
        if len(matching_words) > 1:
            for word in matching_words[1:]:
                derived_word += word["c"]
        return derived_word

    if len(matching_words) == 0:
        return [], ''
    return matching_words, join_word(matching_words)


def draw_rect(image, rect):
    color = (0,0,0) # black
    start_point = (rect[0], rect[1])
    end_point = (rect[2], rect[3])
    image = cv2.rectangle(image, start_point, end_point, color,-1)
    image = cv2.rectangle(image, start_point, end_point, color,20)
    return image

def calc_coverage(word_bbox, reference_bbox):
    '''
    Function to calculate coverage of drawn bbox and word bboxes

    Args:
        word_bbox (list) - box 
    '''
    def calc_iou(bbox1, bbox2):
        """
        Calculate the Intersection over Union (IoU) of two bounding boxes.
        bbox = [x1, y1, x2, y2]

        Args:
        bbox1 : list
            The (x1, y1) position is at the top left corner,
            the (x2, y2) position is at the bottom right corner
        bbox2 : list
            The (x1, y1) position is at the top left corner,
            the (x2, y2) position is at the bottom right corner

        Returns:
        float
            in [0, 1]
        """
        assert bbox1[0] < bbox1[2]
        assert bbox1[1] < bbox1[3]
        assert bbox2[0] < bbox2[2]
        assert bbox2[1] < bbox2[3]
        x_left = max(bbox1[0], bbox2[0])
        y_top = max(bbox1[1], bbox2[1])
        x_right = min(bbox1[2], bbox2[2])
        y_bottom = min(bbox1[3], bbox2[3])

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        intersection_area = (x_right - x_left) * (y_bottom - y_top)

        bbox1_area = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        bbox2_area = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])

        iou = intersection_area / float(bbox1_area + bbox2_area - intersection_area)
        # iou = intersection_area / float(bbox1_area)
        assert iou >= 0.0
        assert iou <= 1.0
        return iou

    if (
        word_bbox[0] > reference_bbox[0]
        and word_bbox[2] < reference_bbox[2]
        and word_bbox[1] > reference_bbox[1]
        and word_bbox[3] < reference_bbox[3]
    ):
        return 1
    else:
        return calc_iou(word_bbox, reference_bbox)