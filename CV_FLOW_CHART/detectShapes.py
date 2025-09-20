import cv2
import imutils


class ShapeDetector:

    def __init__(self):
        pass
	
    def get_rect(self, approx):
        n = approx.ravel() 
        i = 0
        min_x = 100000
        min_y = 100000
        max_x = -1
        max_y = -1

        for j in n :
            if(i % 2 == 0):
                x = n[i]
                y = n[i + 1]
    
                if min_x > x:
                    min_x = x
                if min_y>y:
                    min_y = y
                if max_x < x:
                    max_x = x
                if max_y < y:
                    max_y = y
                
            i = i + 1
        return [min_x, min_y, max_x, max_y]
    def detect(self, c):
        # initialize the shape name and approximate the contour
        shape = "unidentified"
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.04 * peri, True)

        # if the shape is a triangle, it will have 3 vertices
        if len(approx) == 3:
            shape = "triangle"
        # if the shape has 4 vertices, it is either a square or
        # a rectangle
        elif len(approx) == 4:
            # compute the bounding box of the contour and use the
            # bounding box to compute the aspect ratio
            (x, y, w, h) = cv2.boundingRect(approx)
            ar = w / float(h)
            # a square will have an aspect ratio that is approximately
            # equal to one, otherwise, the shape is a rectangle
            shape = "square" if ar >= 0.95 and ar <= 1.05 else "rectangle"
        # if the shape is a pentagon, it will have 5 vertices
        elif len(approx) == 5:
            shape = "pentagon"
        # otherwise, we assume the shape is a circle
        else:
            shape = "circle"
        # return the name of the shape
        return [shape, self.get_rect(approx)]
    
    def draw_rect(self, image, rect):
        color = (0,0,0) # black
        start_point = (rect[0], rect[1])
        end_point = (rect[2], rect[3])
        image = cv2.rectangle(image, start_point, end_point, color,-1)
        image = cv2.rectangle(image, start_point, end_point, color,20)
        return image

    def detect_shape_helper(self, image):
        # cv2.imwrite("removed_components.png", image)
        detected_shapes = []
        ratio = 1.0
        height = image.shape[0]
        width = image.shape[1]
        

        cnts = cv2.findContours(image.copy(), cv2.RETR_TREE,
            cv2.CHAIN_APPROX_NONE,)
        cnts = imutils.grab_contours(cnts)

        # loop over the contours
        
        # the first connected component is all the components joined as one if number of components is greater than one
        if len(cnts)>1:
            cnts = cnts[1:]
        
        for c in cnts:
            # compute the center of the contour, then detect the name of the
            # shape using only the contour
            area = cv2.contourArea(c)
            # print(area)
            if area > 2000:
                M = cv2.moments(c)
                
                cX = int((M["m10"] / (M["m00"]+1)) * ratio)
                cY = int((M["m01"] / (M["m00"]+1)) * ratio)
                shape, rect = self.detect(c)
                
                image = self.draw_rect(image, rect)
                rect_scaled = [float(rect[0])/float(width),float(rect[1]-20)/float(height), float(rect[2])/float(width), float(rect[3]+20)/float(height)]
                # multiply the contour (x, y)-coordinates by the resize ratio,
                # then draw the contours and the name of the shape on the image
                c = c.astype("float")
                c *= ratio
                c = c.astype("int")
                # cv2.drawContours(image, [c], -1, (0, 0, 255), 2)
                # cv2.putText(image, shape, (cX-200, cY), cv2.FONT_HERSHEY_SIMPLEX,
                    # 5, (255, 255, 255),5)
                # detected_shapes.append({ "approx_rect": rect_scaled,"rect": rect, "countour": c,  "shape": shape})
                detected_shapes.append({ "approx_rect": rect_scaled,"rect": rect,  "shape": shape})

        
        # cv2.imwrite("removed_components.png", image)
        return detected_shapes

    def detect_shapes_from_components(self, components, small_components):
        detected = []
        # image = cv2.imread(image_path)
        # image = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        # image = cv2.threshold(image, 0, 255,cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        for component in components:
            detected.extend(self.detect_shape_helper(component))

        for comp in small_components:
            detected.extend(self.detect_shape_helper(comp))
        # cv2.imwrite("removed_shapes.png", image)
        
        return detected
    
    def detect_shapes(self, image_path):
        base_name = ".".join(image_path.split(".")[:-1])
        image = cv2.imread(image_path)
        # cv2.imwrite(base_name + "_detected_shapes.png", image)
        # resized = imutils.resize(image, width=300)
        # ratio = image.shape[0] / float(resized.shape[0])
        # convert the resized image to grayscale, blur it slightly,
        # and threshold it
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        # thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)[1]
        # find contours in the thresholded image and initialize the
        # shape detector
        ratio = 1.0
        cnts = cv2.findContours(gray.copy(), cv2.RETR_TREE,
            cv2.CHAIN_APPROX_NONE,)
        cnts = imutils.grab_contours(cnts)
        # sd = ShapeDetector()
        # loop over the contours
        if len(cnts)>1:
            cnts = cnts[1:]
        for c in cnts:
            # compute the center of the contour, then detect the name of the
            # shape using only the contour
            M = cv2.moments(c)
            
            cX = int((M["m10"] / (M["m00"]+1)) * ratio)
            cY = int((M["m01"] / (M["m00"]+1)) * ratio)
            shape, rect = self.detect(c)
            # multiply the contour (x, y)-coordinates by the resize ratio,
            # then draw the contours and the name of the shape on the image
            c = c.astype("float")
            c *= ratio
            c = c.astype("int")
            cv2.drawContours(image, [c], -1, (0, 0, 255), 2)
            cv2.putText(image, shape, (cX-200, cY), cv2.FONT_HERSHEY_SIMPLEX,
                5, (255, 255, 255),5)
            # cv2.imwrite(base_name + "_detected_shapes.png", image)
            # show the output image
        # cv2.imwrite(base_name + "_detected_shapes.png", image)

if __name__=="__main__":
    # input_image_path = "/home/mohit/cv/converted_OrgChart 1_detected_components_213.png"
    input_image_path = "/home/mohit/cv/converted_OrgChart 1_detcted_lines.png" 
    sd = ShapeDetector()

    sd.detect_shapes(input_image_path)