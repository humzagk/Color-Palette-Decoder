
from PIL import Image
import io
import requests

# This code provides a fast easy and reliable solution to Find the color palette of any image
# Even though anyone can use external internet access to upload the image to a color palette generator,
# So I wrote a function that calculates the most common colors in the image.

# Let's open the image first and analyze it.
image_path = 'output-onlinepngtools.png' #Add your image path here
image = Image.open(image_path)

# Convert image to RGB
image = image.convert('RGB')

# Resize the image to reduce the number of pixels to process
image = image.resize((150, 150))

# Get colors from image
colors = image.getcolors(150*150) # This will get us the count of colors

# Sort colors based on count
sorted_colors = sorted(colors, key=lambda x: x[0], reverse=True)

# Now we'll extract a palette (up to 10 colors)
palette = [color[1] for color in sorted_colors[:10]]

palette