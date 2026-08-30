import os
import cv2
import numpy as np

class Georeferencer:
    def __init__(self, tab_file_path):
        """
        Initializes the Georeferencer by parsing the master DARTIS .tab map.
        We extract the 4 GPS corners (Upper-Left, Upper-Right, Bottom-Right, Bottom-Left)
        for every single image in the dataset.
        """
        self.image_metadata = {}
        self._parse_tab_file(tab_file_path)

    def _parse_tab_file(self, file_path):
        print(f"[*] Parsing Master Map: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        header = None
        for i, line in enumerate(lines):
            if line.startswith("Image set"):
                header = line.strip().split('\t')
                continue
            
            # If we found the header and this line isn't a comment, parse the data
            if header and not line.startswith('/*') and line.strip():
                data = line.strip().split('\t')
                if len(data) >= 17:  # We need at least up to the patch_bl_lat
                    img_name = data[1]
                    
                    # Some files have duplicate entries for multiple objects, 
                    # but the patch GPS corners are the same, so we just grab the first one.
                    if img_name not in self.image_metadata:
                        try:
                            self.image_metadata[img_name] = {
                                'width': float(data[8]),
                                'height': float(data[9]),
                                'ul': (float(data[10]), float(data[11])), # (Lon, Lat)
                                'ur': (float(data[12]), float(data[13])),
                                'br': (float(data[14]), float(data[15])),
                                'bl': (float(data[16]), float(data[17]))
                            }
                        except ValueError:
                            # Skip lines with bad data
                            continue

    def get_perspective_matrix(self, image_name):
        """
        Calculates a 3x3 Perspective Transformation Matrix using OpenCV.
        This maps 2D image pixels exactly to 2D Earth GPS coordinates.
        """
        if image_name not in self.image_metadata:
            raise ValueError(f"Image {image_name} not found in the master .tab file.")

        meta = self.image_metadata[image_name]
        
        # Source points: The 4 corners of the image in Pixels (X, Y)
        w, h = meta['width'], meta['height']
        src_pts = np.array([
            [0, 0],       # Upper Left
            [w, 0],       # Upper Right
            [w, h],       # Bottom Right
            [0, h]        # Bottom Left
        ], dtype=np.float32)

        # Destination points: The 4 corners of the image in GPS (Longitude, Latitude)
        dst_pts = np.array([
            meta['ul'],
            meta['ur'],
            meta['br'],
            meta['bl']
        ], dtype=np.float32)

        # Calculate the perspective transform matrix mathematically
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        return matrix, w, h

    def pixels_to_gps(self, image_name, pixel_contours):
        """
        Converts an array of OpenCV pixel contours into Real-World GPS coordinates.
        """
        matrix, w, h = self.get_perspective_matrix(image_name)
        
        gps_contours = []
        for contour in pixel_contours:
            # OpenCV contours have shape (N, 1, 2). We cast to float32 for transformation.
            contour_pts = contour.astype(np.float32)
            
            # Apply the 3x3 transformation matrix to all points at once
            gps_pts = cv2.perspectiveTransform(contour_pts, matrix)
            
            # Extract just the (Lon, Lat) values
            gps_polygon = gps_pts.reshape(-1, 2).tolist()
            gps_contours.append(gps_polygon)
            
        return gps_contours
