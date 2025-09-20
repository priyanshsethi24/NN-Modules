import cv2
import numpy as np
from config.log import logger

import numpy
import math

class HoughBundler:     
    def __init__(self,min_distance=5,min_angle=2):
        self.min_distance = min_distance
        self.min_angle = min_angle
    
    def get_orientation(self, line):
        orientation = math.atan2(abs((line[3] - line[1])), abs((line[2] - line[0])))
        return math.degrees(orientation)

    def check_is_line_different(self, line_1, groups, min_distance_to_merge, min_angle_to_merge):
        for group in groups:
            for line_2 in group:
                if self.get_distance(line_2, line_1) < min_distance_to_merge:
                    orientation_1 = self.get_orientation(line_1)
                    orientation_2 = self.get_orientation(line_2)
                    if abs(orientation_1 - orientation_2) < min_angle_to_merge:
                        group.append(line_1)
                        return False
        return True

    def distance_point_to_line(self, point, line):
        px, py = point
        x1, y1, x2, y2 = line

        def line_magnitude(x1, y1, x2, y2):
            line_magnitude = math.sqrt(math.pow((x2 - x1), 2) + math.pow((y2 - y1), 2))
            return line_magnitude

        lmag = line_magnitude(x1, y1, x2, y2)
        if lmag < 0.00000001:
            distance_point_to_line = 9999
            return distance_point_to_line

        u1 = (((px - x1) * (x2 - x1)) + ((py - y1) * (y2 - y1)))
        u = u1 / (lmag * lmag)

        if (u < 0.00001) or (u > 1):
            #// closest point does not fall within the line segment, take the shorter distance
            #// to an endpoint
            ix = line_magnitude(px, py, x1, y1)
            iy = line_magnitude(px, py, x2, y2)
            if ix > iy:
                distance_point_to_line = iy
            else:
                distance_point_to_line = ix
        else:
            # Intersecting point is on the line, use the formula
            ix = x1 + u * (x2 - x1)
            iy = y1 + u * (y2 - y1)
            distance_point_to_line = line_magnitude(px, py, ix, iy)

        return distance_point_to_line

    def get_distance(self, a_line, b_line):
        dist1 = self.distance_point_to_line(a_line[:2], b_line)
        dist2 = self.distance_point_to_line(a_line[2:], b_line)
        dist3 = self.distance_point_to_line(b_line[:2], a_line)
        dist4 = self.distance_point_to_line(b_line[2:], a_line)

        return min(dist1, dist2, dist3, dist4)

    def merge_lines_into_groups(self, lines):
        groups = []  # all lines groups are here
        # first line will create new group every time
        groups.append([lines[0]])
        # if line is different from existing gropus, create a new group
        for line_new in lines[1:]:
            if self.check_is_line_different(line_new, groups, self.min_distance, self.min_angle):
                groups.append([line_new])

        return groups

    def merge_line_segments(self, lines):
        orientation = self.get_orientation(lines[0])
      
        if(len(lines) == 1):
            return np.block([[lines[0][:2], lines[0][2:]]])

        points = []
        for line in lines:
            points.append(line[:2])
            points.append(line[2:])
        if 45 < orientation <= 90:
            #sort by y
            points = sorted(points, key=lambda point: point[1])
        else:
            #sort by x
            points = sorted(points, key=lambda point: point[0])

        return np.block([[points[0],points[-1]]])

    def process_lines(self, lines):
        lines_horizontal  = []
        lines_vertical  = []
  
        for line_i in [l[0] for l in lines]:
            orientation = self.get_orientation(line_i)
            # if vertical
            if 45 < orientation <= 90:
                lines_vertical.append(line_i)
            else:
                lines_horizontal.append(line_i)

        lines_vertical  = sorted(lines_vertical , key=lambda line: line[1])
        lines_horizontal  = sorted(lines_horizontal , key=lambda line: line[0])
        merged_lines_all = []

        # for each cluster in vertical and horizantal lines leave only one line
        for i in [lines_horizontal, lines_vertical]:
            if len(i) > 0:
                groups = self.merge_lines_into_groups(i)
                merged_lines = []
                for group in groups:
                    merged_lines.append(self.merge_line_segments(group))
                merged_lines_all.extend(merged_lines)
                    
        return np.asarray(merged_lines_all)

def detect_lines(image_path):
    output_path = ".".join(image_path.split(".")[:-1]) + "_detcted_lines.png"
    # Read image
    image = cv2.imread(image_path)
    
    # Convert image to grayscale
    gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    kernel = np.ones((1, 99), np.uint8)
    kernel_2 = np.ones((9, 9999), np.uint8)
    
    # cv2.imwrite(output_path, gray)
    # The first parameter is the original image,
    # kernel is the matrix with which image is
    # convolved and third parameter is the number
    # of iterations, which will determine how much
    # you want to erode/dilate a given image.

    img_dilation = cv2.dilate(gray, kernel, iterations=2)
    img_erosion = cv2.erode(img_dilation, kernel, iterations=1)
    # blur = cv2.GaussianBlur(gray, (5,5),0.5, 1.0)
    # img_dilation = cv2.dilate(img_erosion, kernel, iterations=1)
    # img_erosion = cv2.erode(img_dilation, kernel, iterations=1) 
    thresh = cv2.threshold(img_erosion, 127, 255,cv2.THRESH_BINARY_INV)[1]
    # Use canny edge detection
    edges = cv2.Canny(thresh.copy(),100,200,apertureSize=3)

    # cv2.imwrite(output_path, img_dilation)
    # cv2.imwrite(output_path, thresh) 
    # cv2.imwrite(output_path, edges)
    
    # Apply HoughLinesP method to
    # to directly obtain line end points
    lines_list =[]
    lines = cv2.HoughLinesP(
                edges.copy(), # Input edge image
                1, # Distance resolution in pixels
                np.pi/180, # Angle resolution in radians
                threshold=20, # Min number of votes for valid line
                minLineLength=20, # Min allowed length of line
                maxLineGap=5 # Max allowed gap between line for joining them
                )
    bundler = HoughBundler(min_distance=10,min_angle=5)
    lines = bundler.process_lines(lines)
    # Iterate over points
    for points in lines:
        # Extracted points nested in the list
        x1,y1,x2,y2=points[0]
        # Draw the lines joing the points
        # On the original image
        cv2.line(image,(x1,y1),(x2,y2),(0,255,0),2)
        # Maintain a simples lookup list for points
        lines_list.append([(x1,y1),(x2,y2)])
        
    # Save the result image
    cv2.imwrite(output_path, image)
    return output_path


def get_equidean_dist(point1, point2):
    x1 = point1[0]
    y1 = point1[1]

    x2 = point2[0]
    y2 = point2[1]
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)


def is_intersecting_horizontel(prev, curr):
    tolerance = 15
    if abs(prev[1] - curr[1]) > tolerance:
        return False
    return True

def is_intersecting_vertical(prev, curr):
    tolerance = 15
    if abs(prev[0] - curr[0]) > tolerance:
        return False
    return True

def filter_close_points(points):
    '''
    Remove corners that are close enough
    '''
    if points is None:
        return points
    
    len_corners = len(points)
    
    
    i = 1
    filtered_corners = []
    while(i<len_corners):
        curr = points[i]
        prev = points[i-1]
        if get_equidean_dist(curr, prev) > 10:
            filtered_corners.append(prev)
            
        if i==len_corners-1:
            filtered_corners.append(curr)
        i +=1

    return filtered_corners

def get_line(points):
    i = 1
    lines = []
    while i<len(points):
        if i%2:
            lines.append([points[i-1], points[i]])
        i +=1
    return lines
            
def make_horizontel_lines(points):
    try:
        
        num_of_points = len(points)
        points.sort(key= lambda x: (x[1], x[0]))
        i = 0
        j = 1
        data = { "lines": [], "points": []}

        while i< num_of_points-1 and j<num_of_points:
            prev = points[i]
            temp_line = [prev]
            j = i+1
            while j<num_of_points:
                
                curr = points[j]
                if is_intersecting_horizontel(prev, curr):
                    temp_line.append(curr)
                    j +=1
                    if j==num_of_points:
                        temp_points = [point for point in temp_line]
                        temp_points.sort(key= lambda x: x[0])
                        
                        temp_points = filter_close_points(temp_points)
                        temp_line = get_line(temp_points)
                        data["lines"].append(temp_line)
                        data["points"].extend(temp_points)
                        
                else:
                    if len(temp_line)>1:
                        temp_line.sort(key= lambda x: x[0])
                    
                        temp_points = filter_close_points(temp_line)
                        temp_line = get_line(temp_points)
                        data["lines"].append(temp_line)
                        data["points"].extend(temp_points)
                    
                    i = j
                    j +=1
                    break
        



    except Exception as e:
        logger.info(e)
    return data

def make_vertical_lines(points):
    try:
        
        num_of_points = len(points)
        points.sort(key= lambda x: (x[0], x[1]))
        i = 0
        j = 1
        data = { "lines": [], "points": []}

        while i< num_of_points-1 and j<num_of_points:
            prev = points[i]
            temp_line = [prev]
            j = i+1
            while j<num_of_points:
                
                curr = points[j]
                if is_intersecting_vertical(prev, curr):
                    temp_line.append(curr)
                    j +=1
                    if j==num_of_points and len(temp_line)>1:
                        temp_points = [point for point in temp_line]
                        temp_points.sort(key= lambda x: x[1])
                        temp_points = filter_close_points(temp_points)
                        temp_line = get_line(temp_points)
                        data["lines"].append(temp_line)
                        data["points"].extend(temp_points)
                        
                else:
                    if len(temp_line)>1:
                        temp_line.sort(key= lambda x: x[1])
                        temp_line = filter_close_points(temp_line)
                        temp_line = get_line(temp_line)
                        data["lines"].append(temp_line)
                        data["points"].extend(temp_line)
                    
                    i = j
                    j +=1
                    break
        



    except Exception as e:
        logger.info(e)
    return data


def draw_rect(image, rect):
    color = (0,0,0) # black
    start_point = (rect[0], rect[1])
    end_point = (rect[2], rect[3])
    image = cv2.rectangle(image, start_point, end_point, color,-1)
    image = cv2.rectangle(image, start_point, end_point, color,20)
    return image

def detect_lines_helper(image_path, shape_components, other_components):

    output_path = ".".join(image_path.split(".")[:-1]) + "_detcted_lines.png"
    # Read image
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255,cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    for component in shape_components:
        thresh = draw_rect(thresh, component["rect"])
    
    cv2.imwrite(output_path,thresh)

    # black_canvas = np.zeros_like(thresh.shape,dtype=np.uint8)
    # black_canvas.fill(255) # or img[:] = 255
    # black_canvas = cv2.cvtColor(black_canvas, cv2.COLOR_GRAY2BGR)
    # oc = numpy.array(other_components).reshape((-1,1,2)).astype(numpy.int32)

    # cv2.drawContours(black_canvas, oc, -1, 255, cv2.FILLED)
    
    # horizontal = black_canvas.copy()
    # vertical = black_canvas.copy()

    horizontal = thresh.copy()
    vertical = thresh.copy()

    cv2.imwrite(output_path, horizontal)
    # [horiz]
    # Specify size on horizontal axis
    cols = horizontal.shape[1]
    horizontal_size = cols // 80
    # Create structure element for extracting horizontal lines through morphology operations
    horizontalStructure = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal_size, 1))
    # Apply morphology operations
    horizontal = cv2.erode(horizontal, horizontalStructure)
    horizontal = cv2.dilate(horizontal, horizontalStructure)
    

    cv2.imwrite(output_path, horizontal)
    maxCorners = 200
    qualityLevel = 0.4
    minDistance = 5
    corners = cv2.goodFeaturesToTrack(horizontal, maxCorners, qualityLevel, minDistance)
    if corners is not None:
        corners = [[corner[0][0],corner[0][1]] for corner in corners]
    else:
        corners = []
    horizontel_lines = make_horizontel_lines(corners)
    
    if horizontel_lines:
        for horizontel_segments in horizontel_lines["lines"]:
            for horizontel_segment in horizontel_segments:
                pointA = horizontel_segment[0]
                pointB = horizontel_segment[1]
                x1 = int(pointA[0])
                y1 = int(pointA[1])

                x2 = int(pointB[0])
                y2 = int(pointB[1])

                cv2.rectangle(image, (x1, y1), (x2, y2), (255, 255, 0), 3)
                vertical = draw_rect(vertical, [x1,y1,x2,y2])
                cv2.circle(image,(x1,y1),5,(36,255,12),-1)
                cv2.circle(image,(x2,y2),5,(36,255,12),-1)
            cv2.imwrite(output_path, image)

    # cv2.imwrite(output_path, horizontal)
    # cv2.imwrite(output_path, vertical)
    # cv2.imwrite(output_path, image)

    # [vert]
    # Specify size on vertical axis
    rows = vertical.shape[0]
    verticalsize = rows // 80
    qualityLevel = 0.4
    minDistance = 3
    
    # dst = cv2.Canny(vertical, 50, 200, None, 3)
    # cv2.imwrite('canny.png', dst)
    

    # linesP = cv2.HoughLinesP(dst, 1, np.pi / 180, 50, None, 50, 10)

    # if linesP is not None:
    #     for i in range(0, len(linesP)):
    #         l = linesP[i][0]
    #         cv2.line(image, (l[0], l[1]), (l[2], l[3]), (0,0,255), 3, cv2.LINE_AA)
    #         cv2.imwrite(output_path, image)
    
    # Create structure element for extracting vertical lines through morphology operations
    verticalStructure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, verticalsize))
    # Apply morphology operations
    
    vertical = cv2.erode(vertical, verticalStructure)
    vertical = cv2.dilate(vertical, verticalStructure)
    cv2.imwrite(output_path, vertical)
    corners_2 = cv2.goodFeaturesToTrack(vertical, maxCorners, qualityLevel, minDistance)
    corners_2 = [[corner[0][0], corner[0][1]] for corner in corners_2]
    vertical_lines = make_vertical_lines(corners_2)
    
    
    if vertical_lines:
        for vertical_segments in vertical_lines["lines"]:
            for vertical_segment in vertical_segments:
                pointA = vertical_segment[0]
                pointB = vertical_segment[1]
                x1 = int(pointA[0])
                y1 = int(pointA[1])

                x2 = int(pointB[0])
                y2 = int(pointB[1])

                cv2.rectangle(image, (x1, y1), (x2, y2), (255, 255, 0), 3)
                cv2.circle(image,(x1,y1),5,(36,255,12),-1)
                cv2.circle(image,(x2,y2),5,(36,255,12),-1)

            cv2.imwrite(output_path, image)

    cv2.imwrite(output_path, image)
    
    print("DONE")
    return {"horizontel_lines": horizontel_lines, "vertical_lines": vertical_lines}
    

def detect_lines_with_components(image_path, components):
    image = cv2.imread(image_path)
    for component in components:
        
        component["countour"] 

if __name__=="__main__":
    input_image_path = "/home/mohit/cv/converted_OrgChart 1_detected_components_213.png"
    # input_image_path = "/home/mohit/cv/removed_components.png"
    # output_path = detect_lines(input_image_path)
    detect_lines_helper(input_image_path)