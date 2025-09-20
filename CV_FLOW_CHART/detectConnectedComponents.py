import cv2
import numpy as np
from bbox_helper import draw_rect

def detect_components(image_path):
    components = []
    small_components = []
    other_components = []
    output_path = ".".join(image_path.split(".")[:-1]) + "_detected_components"
    areas = []
    # Read image
    image = cv2.imread(image_path)
    
    # Convert image to grayscale
    gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255,cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    # thresh = cv2.dilate(thresh, np.zeros(10,10))
    # thresh = cv2.erode(thresh,  np.zeros(10,10))
    # cv2.imwrite(output_path + ".png",thresh)
    # mask = np.zeros(gray.shape, dtype="uint8")
    # Apply connectedCOmponentsWithStats method to
    # to directly obtain connected components lables end points
   
    output = cv2.connectedComponentsWithStats(thresh, 8, cv2.CV_32S)
    (numLabels, labels, stats, centroids) = output
    output_copy = gray.copy()
    # cv2.imwrite("{}_components.png".format(output_path), output_copy)
    # loop over the number of unique connected component labels
    for i in range(0, numLabels):
        # if this is the first component then we examine the
        # *background* (typically we would just ignore this
        # component in our loop)
        if i == 0:
            text = "examining component {}/{} (background)".format(
                i + 1, numLabels)
            continue
        # otherwise, we are examining an actual connected component
        else:
            text = "examining component {}/{}".format( i + 1, numLabels)
        # print a status message update for the current connected
        # component
        # print("[INFO] {}".format(text))
        # extract the connected component statistics and centroid for
        # the current label
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        area = stats[i, cv2.CC_STAT_AREA]
        (cX, cY) = centroids[i]
        if area > 8000:
            areas.append(area)
            print("[INFO] {}".format(text))
            print(area)

            # clone our original image (so we can draw on it) and then draw
            # a bounding box surrounding the connected component along with
            # a circle corresponding to the centroid
            
            # cv2.rectangle(output_copy, (x, y), (x + w, y + h), (0, 255, 0), 3)
            # cv2.circle(output, (int(cX), int(cY)), 4, (0, 0, 255), -1)
            # construct a mask for the current connected component by
            # finding a pixels in the labels array that have the current
            # connected component ID
            componentMask = (labels == i).astype("uint8") * 255
            components.append(componentMask)
            # cv2.imwrite(output_path + f"_{i}.png", componentMask)
        elif area <= 8000 and area > 1500:
            componentMask = (labels == i).astype("uint8") * 255
            small_components.append(componentMask)
        # else:
        #     componentMask = (labels == i).astype("uint8") * 255
        #     other_components.append(componentMask)

            
    
    # Save the result image
    # cv2.imwrite(output_path + ".png", mask)
    return components, small_components, other_components


if __name__=="__main__":
    # input_image_path = "OrgChart 2.png"
    input_image_path = "/home/mohit/cv/converted_OrgChart 1_detcted_lines.png"
    detect_components(input_image_path)