import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

METHODS = ["hsv_focus", "adaptive", "grabcut"]
DEFAULT_METHOD = "adaptive"


def detect_subject(image_path, method=DEFAULT_METHOD, **kwargs):
    """
    Detect the subject in an image with a solid colored background.
    Returns a binary mask where 255 represents the subject and 0 represents the background.

    Args:
        image_path (str): Path to the input image
        method (str): Detection method - one of "hsv_focus", "adaptive", "grabcut"
        **kwargs: Method-specific parameters (see individual methods)

    Returns:
        np.ndarray: Binary mask (uint8, 0 or 255)
    """
    if method == "hsv_focus":
        return _detect_hsv_focus(image_path, **kwargs)
    elif method == "adaptive":
        return _detect_adaptive(image_path, **kwargs)
    elif method == "grabcut":
        return _detect_grabcut(image_path, **kwargs)
    else:
        raise ValueError(f"Unknown masking method: {method}. Choose from: {METHODS}")


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def _sample_background_color(image, border_fraction=0.05):
    """Sample background color statistics from image corners (LAB space).

    Uses corners rather than full border strips to avoid sampling specimen
    pixels when the specimen is large or near the edges.
    """
    h, w = image.shape[:2]
    bh = max(int(h * border_fraction), 4)
    bw = max(int(w * border_fraction), 4)

    # Collect pixels from the four corners only
    tl = image[:bh, :bw].reshape(-1, 3)
    tr = image[:bh, -bw:].reshape(-1, 3)
    bl = image[-bh:, :bw].reshape(-1, 3)
    br = image[-bh:, -bw:].reshape(-1, 3)
    corner_pixels = np.vstack([tl, tr, bl, br]).astype(np.float64)

    mean = np.mean(corner_pixels, axis=0)
    cov = np.cov(corner_pixels.T)
    # Regularize covariance to avoid singular matrix
    cov += np.eye(3) * 1e-5
    return mean, cov


def _mahalanobis_distance_map(image_lab, mean, cov):
    """Compute per-pixel Mahalanobis distance from background distribution."""
    pixels = image_lab.reshape(-1, 3).astype(np.float64)
    diff = pixels - mean
    cov_inv = np.linalg.inv(cov)
    # Vectorized Mahalanobis: sqrt(diff @ cov_inv @ diff.T) per pixel
    left = diff @ cov_inv
    dist_sq = np.sum(left * diff, axis=1)
    dist_sq = np.clip(dist_sq, 0, None)
    dist = np.sqrt(dist_sq)
    return dist.reshape(image_lab.shape[:2])


def _flood_fill_background(mask):
    """Fill holes in a binary mask by flood-filling from the border."""
    bordered = cv2.copyMakeBorder(mask, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    flood = bordered.copy()
    h, w = bordered.shape
    ff_mask = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(flood, ff_mask, (0, 0), 255)
    flood_inv = cv2.bitwise_not(flood)
    result = bordered | flood_inv
    return result[1:-1, 1:-1]


def _keep_specimen_components(mask):
    """Keep all components whose centroids fall within or near the convex hull
    of the largest component, preserving detached legs/antennae."""
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask)
    if num_labels <= 1:
        return mask

    # Find largest component (skip background label 0)
    areas = stats[1:, cv2.CC_STAT_AREA]
    largest_label = 1 + np.argmax(areas)
    largest_area = areas[largest_label - 1]

    # Get convex hull of the largest component
    largest_mask = (labels == largest_label).astype(np.uint8) * 255
    contours, _ = cv2.findContours(largest_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return largest_mask

    hull = cv2.convexHull(contours[0])
    # Dilate the hull region to be generous with nearby components
    hull_mask = np.zeros_like(mask)
    cv2.fillConvexPoly(hull_mask, hull, 255)
    # Expand hull region by 5% of image diagonal
    diag = int(np.sqrt(mask.shape[0]**2 + mask.shape[1]**2) * 0.05)
    if diag > 0:
        hull_mask = cv2.dilate(hull_mask, np.ones((diag, diag), np.uint8), iterations=1)

    # Keep components that overlap with the expanded hull or are large enough
    min_keep_area = largest_area * 0.001  # keep components > 0.1% of largest
    result = np.zeros_like(mask)
    for label_id in range(1, num_labels):
        component_mask = (labels == label_id).astype(np.uint8) * 255
        # Check overlap with hull region
        overlap = cv2.bitwise_and(component_mask, hull_mask)
        if np.any(overlap) and stats[label_id, cv2.CC_STAT_AREA] > min_keep_area:
            result = cv2.bitwise_or(result, component_mask)

    return result


def _smooth_mask_edges(mask, sigma=1.0):
    """Apply slight Gaussian blur to smooth binary mask edges."""
    smoothed = gaussian_filter(mask.astype(np.float64), sigma=sigma)
    return (smoothed > 127).astype(np.uint8) * 255


# ---------------------------------------------------------------------------
# Method 1: HSV + Focus (original method, preserved for compatibility)
# ---------------------------------------------------------------------------

def _detect_hsv_focus(image_path, saturation_threshold=30, focus_threshold=20,
                      gaussian_kernel_size=3, cleanup_kernel_size=5):
    """Original HSV saturation + Laplacian focus method."""
    image = cv2.imread(image_path)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Saturation-based detection
    saturation = hsv[:, :, 1]
    _, sat_mask = cv2.threshold(saturation, saturation_threshold, 255, cv2.THRESH_BINARY)

    # Focus-based detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
    focus_measure = np.abs(laplacian)
    focus_measure = cv2.GaussianBlur(focus_measure,
                                     (gaussian_kernel_size, gaussian_kernel_size), 0)
    focus_measure = ((focus_measure - focus_measure.min()) * 255 /
                     max(focus_measure.max() - focus_measure.min(), 1e-8))
    focus_measure = focus_measure.astype(np.uint8)
    _, focus_mask = cv2.threshold(focus_measure, focus_threshold, 255, cv2.THRESH_BINARY)

    combined_mask = cv2.bitwise_or(sat_mask, focus_mask)

    kernel = np.ones((cleanup_kernel_size, cleanup_kernel_size), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)

    combined_mask = _flood_fill_background(combined_mask)
    combined_mask = _keep_specimen_components(combined_mask)

    return _smooth_mask_edges(combined_mask, sigma=0.5)


# ---------------------------------------------------------------------------
# Method 2: Adaptive background modeling (new robust default)
# ---------------------------------------------------------------------------

def _detect_adaptive(image_path, border_fraction=0.05, cleanup_kernel_size=5,
                     threshold_multiplier=0.5):
    """Adaptive background-modeling method using Mahalanobis distance in LAB space.

    Automatically adapts to any background color. Uses Otsu's method for automatic
    threshold selection, scaled by threshold_multiplier to control conservatism.

    Args:
        threshold_multiplier (float): Scales Otsu threshold. Lower = keeps more
            foreground (0.1–1.0, default 0.5). Reduce for low-contrast specimens.
    """
    image = cv2.imread(image_path)
    image_lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

    # Step 1: Sample background from image corners
    mean, cov = _sample_background_color(image_lab, border_fraction)

    # Step 2: Compute per-pixel distance from background
    dist_map = _mahalanobis_distance_map(image_lab, mean, cov)

    # Normalize to 0-255 for thresholding
    dist_norm = np.clip(dist_map / max(dist_map.max(), 1e-8) * 255, 0, 255).astype(np.uint8)

    # Step 3: Otsu's automatic thresholding with user-controlled bias
    otsu_thresh, _ = cv2.threshold(dist_norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    conservative_thresh = max(int(otsu_thresh * threshold_multiplier), 1)
    _, coarse_mask = cv2.threshold(dist_norm, conservative_thresh, 255, cv2.THRESH_BINARY)

    # Step 4: Dilate to recover clipped edges before cleanup
    kernel = np.ones((cleanup_kernel_size, cleanup_kernel_size), np.uint8)
    coarse_mask = cv2.dilate(coarse_mask, kernel, iterations=2)

    # Step 5: Morphological cleanup (close gaps, then remove small noise)
    coarse_mask = cv2.morphologyEx(coarse_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    coarse_mask = cv2.morphologyEx(coarse_mask, cv2.MORPH_OPEN, kernel, iterations=1)

    # Step 6: Fill holes
    coarse_mask = _flood_fill_background(coarse_mask)

    # Step 7: Keep specimen components (not just largest)
    coarse_mask = _keep_specimen_components(coarse_mask)

    return _smooth_mask_edges(coarse_mask, sigma=1.0)


# ---------------------------------------------------------------------------
# Method 3: GrabCut refinement (highest quality, slower)
# ---------------------------------------------------------------------------

def _detect_grabcut(image_path, border_fraction=0.05, cleanup_kernel_size=5,
                    grabcut_iterations=5, threshold_multiplier=0.5):
    """Background modeling + GrabCut refinement for highest quality masks.

    Uses adaptive background modeling to generate a generous trimap, then
    refines boundaries with GrabCut for precise edge-following. The coarse
    mask is intentionally conservative (keeps more foreground) so GrabCut
    can make the fine decisions about what is truly background.

    Args:
        threshold_multiplier (float): Scales Otsu threshold. Lower = keeps more
            foreground (0.1–1.0, default 0.5). Reduce for low-contrast specimens.
    """
    image = cv2.imread(image_path)
    image_lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

    # Step 1: Get coarse mask via conservative thresholding
    mean, cov = _sample_background_color(image_lab, border_fraction)
    dist_map = _mahalanobis_distance_map(image_lab, mean, cov)
    dist_norm = np.clip(dist_map / max(dist_map.max(), 1e-8) * 255, 0, 255).astype(np.uint8)

    # Use a conservative threshold scaled by user multiplier
    otsu_thresh, _ = cv2.threshold(dist_norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    conservative_thresh = max(int(otsu_thresh * threshold_multiplier), 1)
    _, coarse_mask = cv2.threshold(dist_norm, conservative_thresh, 255, cv2.THRESH_BINARY)

    kernel = np.ones((cleanup_kernel_size, cleanup_kernel_size), np.uint8)
    # Dilate generously — better to give GrabCut too much than too little
    coarse_mask = cv2.dilate(coarse_mask, kernel, iterations=3)
    coarse_mask = cv2.morphologyEx(coarse_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    coarse_mask = _flood_fill_background(coarse_mask)

    # Step 2: Build trimap from coarse mask
    # Sure foreground: only mildly eroded — preserve specimen interior
    sure_fg = cv2.erode(coarse_mask, kernel, iterations=3)
    # Sure background: well outside the dilated coarse mask
    sure_bg_region = cv2.dilate(coarse_mask, kernel, iterations=7)

    trimap = np.full(coarse_mask.shape, cv2.GC_PR_BGD, dtype=np.uint8)
    trimap[sure_bg_region == 0] = cv2.GC_BGD
    trimap[coarse_mask == 255] = cv2.GC_PR_FGD
    trimap[sure_fg == 255] = cv2.GC_FGD

    # Step 3: Run GrabCut with trimap initialization
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    rect = (0, 0, image.shape[1] - 1, image.shape[0] - 1)

    cv2.grabCut(image, trimap, rect, bgd_model, fgd_model,
                grabcut_iterations, cv2.GC_INIT_WITH_MASK)

    # Step 4: Extract final mask
    refined_mask = np.where(
        (trimap == cv2.GC_FGD) | (trimap == cv2.GC_PR_FGD), 255, 0
    ).astype(np.uint8)

    # Step 5: Cleanup and component selection
    refined_mask = cv2.morphologyEx(refined_mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    refined_mask = _flood_fill_background(refined_mask)
    refined_mask = _keep_specimen_components(refined_mask)

    return _smooth_mask_edges(refined_mask, sigma=1.0)


# ---------------------------------------------------------------------------
# Cutout creation
# ---------------------------------------------------------------------------

def create_cutout(image_path, mask_path=None):
    """Create a cutout image from a stacked image and its mask.

    Produces a JPG with the background set to black, preserving EXIF compatibility.

    Args:
        image_path (str): Path to the original stacked image
        mask_path (str): Path to the binary mask. If None, inferred from image_path.

    Returns:
        str: Path to the saved cutout file
    """
    if mask_path is None:
        mask_path = image_path[:-4] + "_masked.png"

    image = cv2.imread(image_path)
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

    if image is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    if mask is None:
        raise FileNotFoundError(f"Could not read mask: {mask_path}")

    # Smooth mask for cleaner edges
    alpha = cv2.GaussianBlur(mask, (5, 5), 0).astype(np.float32) / 255.0

    # Blend: foreground where mask is white, black where mask is zero
    cutout = (image.astype(np.float32) * alpha[:, :, np.newaxis]).astype(np.uint8)

    cutout_path = image_path[:-4] + '_cutout.jpg'
    cv2.imwrite(cutout_path, cutout)
    return cutout_path


# ---------------------------------------------------------------------------
# Visualization helpers
# ---------------------------------------------------------------------------

def visualize_mask(image_path, mask):
    """Visualize the detected mask overlaid on the original image."""
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    overlay = image_rgb.copy()
    overlay[mask == 255] = [0, 255, 0]
    return cv2.addWeighted(overlay, 0.3, image_rgb, 0.7, 0)
