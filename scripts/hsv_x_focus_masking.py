import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

def detect_subject(image_path, saturation_threshold=30, focus_threshold=20, 
                  gaussian_kernel_size=3, cleanup_kernel_size=5):
    """
    Detect the subject in an image with a solid colored background.
    Returns a binary mask where 1 represents the subject and 0 represents the background.
    
    Args:
        image_path (str): Path to the input image
        saturation_threshold (int): Threshold for saturation-based detection (0-255)
        focus_threshold (int): Threshold for focus-based detection (0-255)
        gaussian_kernel_size (int): Size of kernel for Gaussian blur (odd number)
        cleanup_kernel_size (int): Size of kernel for morphological operations (odd number)
        
    Returns:
        np.ndarray: Binary mask of the same size as input image
    """
    # Read the image
    image = cv2.imread(image_path)
    
    # Convert to different color spaces
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # 1. Color-based detection
    # Extract saturation channel and threshold it
    saturation = hsv[:, :, 1]
    _, sat_mask = cv2.threshold(saturation, saturation_threshold, 255, cv2.THRESH_BINARY)
    
    # 2. Focus-based detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Use a larger kernel size for Laplacian
    laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
    focus_measure = np.abs(laplacian)
    
    # Apply Gaussian blur to reduce noise in focus measure
    focus_measure = cv2.GaussianBlur(focus_measure, 
                                    (gaussian_kernel_size, gaussian_kernel_size), 0)
    
    # Normalize focus measure to 0-255 range
    focus_measure = ((focus_measure - focus_measure.min()) * 255 / 
                    (focus_measure.max() - focus_measure.min()))
    focus_measure = focus_measure.astype(np.uint8)
    
    # Lower threshold for focus measure
    _, focus_mask = cv2.threshold(focus_measure, focus_threshold, 255, cv2.THRESH_BINARY)
    
    # 3. Combine masks
    combined_mask = cv2.bitwise_or(sat_mask, focus_mask)
    
    # 4. Clean up the mask using morphological operations
    # Create a square kernel of ones with the specified size
    kernel = np.ones((cleanup_kernel_size, cleanup_kernel_size), np.uint8)
    
    # First apply morphological closing (dilation followed by erosion)
    # This helps close small holes and connect nearby components
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
    
    # Then apply morphological opening (erosion followed by dilation)
    # This removes small noise and smooths object boundaries while preserving
    # the overall shape and size of larger objects
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
    
    
    # Fill holes in the mask
    # Add a border of background pixels
    bordered_mask = cv2.copyMakeBorder(
        combined_mask,
        top=1, bottom=1, left=1, right=1,
        borderType=cv2.BORDER_CONSTANT,
        value=0
    )
    
    # Perform flood fill on bordered mask
    flood_fill_mask = bordered_mask.copy()
    h, w = bordered_mask.shape
    mask = np.zeros((h+2, w+2), np.uint8)
    cv2.floodFill(flood_fill_mask, mask, (0,0), 255)
    flood_fill_mask_inv = cv2.bitwise_not(flood_fill_mask)
    
    # Combine and remove border
    bordered_result = bordered_mask | flood_fill_mask_inv
    combined_mask = bordered_result[1:-1, 1:-1]  # Remove the border we added
    
    
    # Find the largest connected component
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(combined_mask)
    if num_labels > 1:
        # Skip label 0 (background)
        largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        combined_mask = (labels == largest_label).astype(np.uint8) * 255
    
    # 5. Final refinement
    # Apply slight Gaussian blur to smooth edges
    combined_mask = gaussian_filter(combined_mask, sigma=0.5)
    combined_mask = (combined_mask > 127).astype(np.uint8)
    
    return combined_mask

def visualize_mask(image_path, mask):
    """
    Visualize the detected mask overlaid on the original image.
    
    Args:
        image_path (str): Path to the original image
        mask (np.ndarray): Binary mask to visualize
    """
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Create a colored overlay
    overlay = image_rgb.copy()
    overlay[mask == 1] = [0, 255, 0]  # Green overlay for detected subject
    
    # Blend with original image
    alpha = 0.3
    result = cv2.addWeighted(overlay, alpha, image_rgb, 1 - alpha, 0)
    
    return result

def scale_for_display(image, max_dimension=1200):
    """
    Scale down an image if its dimensions exceed max_dimension while maintaining aspect ratio.
    
    Parameters:
        image (numpy.ndarray): Input image
        max_dimension (int): Maximum allowed dimension (width or height)
        
    Returns:
        numpy.ndarray: Scaled image
    """
    height, width = image.shape[:2]
    
    # If image is smaller than max dimension, return original
    if max(height, width) <= max_dimension:
        return image
        
    # Calculate scaling factor
    scale = max_dimension / max(height, width)
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

if __name__ == "__main__":
    # Path to your test image
    image_path = "grey_stack/stacked/_x_00100_y_00000_.tif"
    
    try:
        # Generate the mask with custom parameters
        mask = detect_subject(
            image_path,
            saturation_threshold=30,  # Adjust based on image characteristics
            focus_threshold=20,       # Adjust based on image characteristics
            gaussian_kernel_size=3,   # Must be odd number
            cleanup_kernel_size=3     # Must be odd number
        )
        
        # Load original image for visualization
        original = cv2.imread(image_path)
        original_rgb = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)
        
        # Create visualization
        visualization = visualize_mask(image_path, mask)
        
        # Scale images for display
        display_original = scale_for_display(original_rgb)
        display_mask = scale_for_display(mask * 255)  # Multiply by 255 for better visibility
        display_viz = scale_for_display(visualization)
        
        # Display results
        cv2.imshow("Original Image", cv2.cvtColor(display_original, cv2.COLOR_RGB2BGR))
        cv2.imshow("Detected Mask", display_mask)
        cv2.imshow("Visualization", cv2.cvtColor(display_viz, cv2.COLOR_RGB2BGR))
        
        # Save results
        cv2.imwrite("mask_result.png", mask * 255)
        cv2.imwrite("visualization_result.png", cv2.cvtColor(visualization, cv2.COLOR_RGB2BGR))
        
        print("Results have been saved as 'mask_result.png' and 'visualization_result.png'")
        
        # Wait for key press and close windows
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
