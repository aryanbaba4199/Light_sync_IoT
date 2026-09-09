import numpy as np

class ColorExtractor:
    @staticmethod
    def extract_ambient_color(img_array: np.ndarray) -> tuple[int, int, int]:
        """
        Extracts a dominant or robust ambient color from an RGB/BGRA frame.
        Expects a numpy array, usually downsampled already.
        Returns (r, g, b)
        """
        if img_array.size == 0:
            return 0, 0, 0
            
        # Flatten the spatial dimensions to a list of pixels
        pixels = img_array.reshape(-1, img_array.shape[-1])
        
        # MSS typically returns BGRA (Blue, Green, Red, Alpha)
        if pixels.shape[-1] == 4:
            b, g, r, _ = pixels.T
        elif pixels.shape[-1] == 3:
            b, g, r = pixels.T # Or RGB if transformed, but assume BGR for raw capture
        else:
            return 0, 0, 0

        # Calculate perceptual luminance
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        
        # Filter out extremely dark pixels (e.g., cinematic black bars or dark shadows)
        # This prevents the ambient lighting from becoming dull gray during dark scenes
        mask = luminance > 15
        
        valid_r = r[mask]
        valid_g = g[mask]
        valid_b = b[mask]
        
        if len(valid_r) == 0:
            # If there are no valid bright pixels, the scene is genuinely dark
            # Return a naive average of everything to get a very dim color
            return int(np.mean(r)), int(np.mean(g)), int(np.mean(b))
            
        # Mean of the valid "illuminated" pixels
        avg_r = int(np.mean(valid_r))
        avg_g = int(np.mean(valid_g))
        avg_b = int(np.mean(valid_b))
        
        return avg_r, avg_g, avg_b
