#!/usr/bin/env python3
"""
Script to generate iOS app icons and splash screens from a source image.
Requires Pillow (PIL) library: pip install Pillow
"""

import os
from PIL import Image, ImageDraw, ImageFont

def create_icon(size, source_image_path, output_path, output_filename, background_color="#ffffff", logo_padding_ratio=0.7):
    """
    Create an app icon of the specified size with the logo centered and aspect ratio preserved.
    :param size: The desired size of the square icon (e.g., 60, 120).
    :param source_image_path: Path to the original logo image.
    :param output_path: Directory to save the generated icon.
    :param output_filename: Filename for the generated icon.
    :param background_color: Hex color code for the icon's background (e.g., "#ffffff" for white).
    :param logo_padding_ratio: How much of the icon's size the logo should occupy (e.g., 0.7 means 70% of the icon's dimension).
                               Lower value means more padding/background visible.
    """
    # Create a new blank square image for the icon with the specified background color
    icon_img = Image.new('RGB', (size, size), background_color)
    
    # Open and prepare the logo
    logo = Image.open(source_image_path)
    
    # Calculate the maximum dimension for the logo within the icon, based on padding ratio
    max_logo_dimension = int(size * logo_padding_ratio)
    
    # Calculate new logo dimensions while maintaining aspect ratio
    logo_width, logo_height = logo.size
    
    # Determine the scaling factor
    if logo_width > logo_height:
        # Logo is wider than it is tall
        new_width = max_logo_dimension
        new_height = int(logo_height * (new_width / logo_width))
    else:
        # Logo is taller than it is wide, or square
        new_height = max_logo_dimension
        new_width = int(logo_width * (new_height / logo_height))

    # Resize the logo with LANCZOS for high quality downsampling
    logo = logo.resize((new_width, new_height), Image.LANCZOS)
    
    # Calculate position to center the logo on the icon image
    x = (size - new_width) // 2
    y = (size - new_height) // 2
    
    # Paste the resized logo onto the icon image
    # Use logo.convert("RGBA") to ensure correct alpha handling if logo is not RGBA
    icon_img.paste(logo, (x, y), logo if logo.mode == 'RGBA' else logo.convert("RGBA"))
    
    # Ensure directory exists
    os.makedirs(output_path, exist_ok=True)
    
    # Save the generated icon
    icon_img.save(os.path.join(output_path, output_filename))
    print(f"Created {output_filename} ({size}x{size}) with background {background_color}")


def create_splash(width, height, logo_path, output_path, output_filename, background_color="#f8f9fa", logo_scale_factor=0.4):
    """Create a splash screen with the logo centered"""
    # Create blank image with specified background color
    img = Image.new('RGB', (width, height), background_color)
    
    # Open and resize logo (to a percentage of the smallest dimension)
    logo = Image.open(logo_path)
    logo_ratio = logo.width / logo.height
    
    # Determine logo size (e.g., 40% of smallest dimension)
    max_logo_dimension_on_splash = min(width, height) * logo_scale_factor
    
    if logo.width > logo.height:
        new_width = max_logo_dimension_on_splash
        new_height = new_width / logo_ratio
    else:
        new_height = max_logo_dimension_on_splash
        new_width = new_height * logo_ratio
    
    logo = logo.resize((int(new_width), int(new_height)), Image.LANCZOS)
    
    # Calculate position to center the logo
    x = (width - logo.width) // 2
    y = (height - logo.height) // 2
    
    # Paste logo onto splash screen
    img.paste(logo, (x, y), logo if logo.mode == 'RGBA' else logo.convert("RGBA"))
    
    # Ensure directory exists
    os.makedirs(output_path, exist_ok=True)
    
    # Save the splash screen
    img.save(os.path.join(output_path, output_filename))
    print(f"Created {output_filename} ({width}x{height})")

def main():
    # Set paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(current_dir, 'static', 'assets')
    source_logo = os.path.join(assets_dir, 'logo.png')
    
    # Check if source logo exists
    if not os.path.exists(source_logo):
        print(f"Error: Source logo not found at {source_logo}")
        return
    
    # --- Configuration for Icon and Splash ---
    # Set your desired icon background color (e.g., "#3498db" for a blue, "#f0f0f0" for light gray)
    ICON_BACKGROUND_COLOR = "#662a97" # Example: Bootstrap primary blue
    # Control how much of the icon space the logo takes (0.0 to 1.0)
    # A smaller value means more background padding around the logo.
    ICON_LOGO_PADDING_RATIO = 0.80 # Logo will occupy 65% of the icon's dimension

    # Set your desired splash screen background color
    SPLASH_BACKGROUND_COLOR = "#f8f9fa" # Bootstrap light background color
    # Control the size of the logo on the splash screen (0.0 to 1.0)
    SPLASH_LOGO_SCALE_FACTOR = 0.4 # Logo will be 40% of the smallest splash dimension

    # Generate app icons for iOS
    # Sizes based on Apple's guidelines (some common ones, can add more)
    icon_sizes = [
        # iOS App Icon (for iPhone, iPad, and App Store)
        # iPhone Notification: 20pt @2x, @3x = 40x40, 60x60
        # iPhone Settings: 29pt @2x, @3x = 58x58, 87x87
        # iPhone Spotlight: 40pt @2x, @3x = 80x80, 120x120
        # iPhone App: 60pt @2x, @3x = 120x120, 180x180
        # iPad Notification: 20pt @1x, @2x = 20x20, 40x40
        # iPad Settings: 29pt @1x, @2x = 29x29, 58x58
        # iPad Spotlight: 40pt @1x, @2x = 40x40, 80x80
        # iPad App: 76pt @1x, @2x = 76x76, 152x152
        # iPad Pro App: 83.5pt @2x = 167x167
        # App Store: 1024x1024 (no @x, just 1024x1024)
        
        # Common sizes you'd use for a PWA or general purpose:
        40,   # iPhone Notification (@2x), iPad Spotlight (@1x)
        58,   # iPhone Settings (@2x), iPad Settings (@2x)
        60,   # iPhone Notification (@3x)
        76,   # iPad App (@1x)
        80,   # iPhone Spotlight (@2x), iPad Spotlight (@2x)
        87,   # iPhone Settings (@3x)
        120,  # iPhone Spotlight (@3x), iPhone App (@2x)
        152,  # iPad App (@2x)
        167,  # iPad Pro 12.9" App
        180,  # iPhone App (@3x)
        1024  # App Store icon (can also be used as a large general icon)
    ]
    
    for size in icon_sizes:
        create_icon(size, source_logo, assets_dir, f"app-icon-{size}.png", 
                    background_color=ICON_BACKGROUND_COLOR, 
                    logo_padding_ratio=ICON_LOGO_PADDING_RATIO)
    
    # Generate splash screens for different iOS devices
    # Note: These are common sizes, actual device sizes can vary and new ones appear.
    # For a robust PWA, consider using media queries for splash screens or a single
    # large splash screen that scales.
    splash_sizes = [
        # iPhone (Portrait) - commonly used sizes for launch images
        (750, 1334, "splash-750x1334.png"),       # iPhone 6, 7, 8
        (1242, 2208, "splash-1242x2208.png"),     # iPhone 6 Plus, 7 Plus, 8 Plus
        (1125, 2436, "splash-1125x2436.png"),     # iPhone X, XS, 11 Pro
        (828, 1792, "splash-828x1792.png"),       # iPhone XR, 11
        (1242, 2688, "splash-1242x2688.png"),     # iPhone XS Max, 11 Pro Max
        (1170, 2532, "splash-1170x2532.png"),     # iPhone 12, 12 Pro, 13, 13 Pro
        (1284, 2778, "splash-1284x2778.png"),     # iPhone 12 Pro Max, 13 Pro Max
        (1179, 2556, "splash-1179x2556.png"),     # iPhone 14, 15
        (1290, 2796, "splash-1290x2796.png"),     # iPhone 14 Pro, 15 Pro
        (1328, 2860, "splash-1328x2860.png"),     # iPhone 14 Pro Max, 15 Pro Max

        # iPad (Portrait)
        (768, 1024, "splash-768x1024.png"),       # iPad Mini, iPad Air (older)
        (1536, 2048, "splash-1536x2048.png"),     # iPad Mini, iPad Air (retina), iPad (5th-9th gen)
        (1668, 2224, "splash-1668x2224.png"),     # iPad Pro 10.5", iPad Air (3rd gen)
        (1668, 2388, "splash-1668x2388.png"),     # iPad Pro 11" (1st, 2nd, 3rd gen), iPad Air (4th, 5th gen)
        (2048, 2732, "splash-2048x2732.png"),     # iPad Pro 12.9" (all generations)
    ]
    
    for width, height, filename in splash_sizes:
        create_splash(width, height, source_logo, assets_dir, filename, 
                      background_color=SPLASH_BACKGROUND_COLOR, 
                      logo_scale_factor=SPLASH_LOGO_SCALE_FACTOR)
    
    print("\nAll iOS web app assets have been generated successfully!")
    print(f"Assets saved to: {assets_dir}")

if __name__ == "__main__":
    main()