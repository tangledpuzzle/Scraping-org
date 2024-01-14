import re
from io import BytesIO
import base64
from .typing import ImageType, Union
from PIL import Image

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def to_image(image: ImageType) -> Image.Image:
    """
    Converts the input image to a PIL Image object.

    Args:
        image (Union[str, bytes, Image.Image]): The input image.

    Returns:
        Image.Image: The converted PIL Image object.
    """
    if isinstance(image, str):
        is_data_uri_an_image(image)
        image = extract_data_uri(image)
    if isinstance(image, bytes):
        is_accepted_format(image)
        image = Image.open(BytesIO(image))
    elif not isinstance(image, Image.Image):
        image = Image.open(image)
        copy = image.copy()
        copy.format = image.format
        image = copy
    return image

def is_allowed_extension(filename: str) -> bool:
    """
    Checks if the given filename has an allowed extension.

    Args:
        filename (str): The filename to check.

    Returns:
        bool: True if the extension is allowed, False otherwise.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_data_uri_an_image(data_uri: str) -> bool:
    """
    Checks if the given data URI represents an image.

    Args:
        data_uri (str): The data URI to check.

    Raises:
        ValueError: If the data URI is invalid or the image format is not allowed.
    """
    # Check if the data URI starts with 'data:image' and contains an image format (e.g., jpeg, png, gif)
    if not re.match(r'data:image/(\w+);base64,', data_uri):
        raise ValueError("Invalid data URI image.")
    # Extract the image format from the data URI
    image_format = re.match(r'data:image/(\w+);base64,', data_uri).group(1)
    # Check if the image format is one of the allowed formats (jpg, jpeg, png, gif)
    if image_format.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError("Invalid image format (from mime file type).")

def is_accepted_format(binary_data: bytes) -> bool:
    """
    Checks if the given binary data represents an image with an accepted format.

    Args:
        binary_data (bytes): The binary data to check.

    Raises:
        ValueError: If the image format is not allowed.
    """
    if binary_data.startswith(b'\xFF\xD8\xFF'):
        pass # It's a JPEG image
    elif binary_data.startswith(b'\x89PNG\r\n\x1a\n'):
        pass # It's a PNG image
    elif binary_data.startswith(b'GIF87a') or binary_data.startswith(b'GIF89a'):
        pass # It's a GIF image
    elif binary_data.startswith(b'\x89JFIF') or binary_data.startswith(b'JFIF\x00'):
        pass # It's a JPEG image
    elif binary_data.startswith(b'\xFF\xD8'):
        pass # It's a JPEG image
    elif binary_data.startswith(b'RIFF') and binary_data[8:12] == b'WEBP':
        pass # It's a WebP image
    else:
        raise ValueError("Invalid image format (from magic code).")

def extract_data_uri(data_uri: str) -> bytes:
    """
    Extracts the binary data from the given data URI.

    Args:
        data_uri (str): The data URI.

    Returns:
        bytes: The extracted binary data.
    """
    data = data_uri.split(",")[1]
    data = base64.b64decode(data)
    return data

def get_orientation(image: Image.Image) -> int:
    """
    Gets the orientation of the given image.

    Args:
        image (Image.Image): The image.

    Returns:
        int: The orientation value.
    """
    exif_data = image.getexif() if hasattr(image, 'getexif') else image._getexif()
    if exif_data is not None:
        orientation = exif_data.get(274)  # 274 corresponds to the orientation tag in EXIF
        if orientation is not None:
            return orientation

def process_image(img: Image.Image, new_width: int, new_height: int) -> Image.Image:
    """
    Processes the given image by adjusting its orientation and resizing it.

    Args:
        img (Image.Image): The image to process.
        new_width (int): The new width of the image.
        new_height (int): The new height of the image.

    Returns:
        Image.Image: The processed image.
    """
    orientation = get_orientation(img)
    if orientation:
        if orientation > 4:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if orientation in [3, 4]:
            img = img.transpose(Image.ROTATE_180)
        if orientation in [5, 6]:
            img = img.transpose(Image.ROTATE_270)
        if orientation in [7, 8]:
            img = img.transpose(Image.ROTATE_90)
    img.thumbnail((new_width, new_height))
    return img

def to_base64(image: Image.Image, compression_rate: float) -> str:
    """
    Converts the given image to a base64-encoded string.

    Args:
        image (Image.Image): The image to convert.
        compression_rate (float): The compression rate (0.0 to 1.0).

    Returns:
        str: The base64-encoded image.
    """
    output_buffer = BytesIO()
    image.save(output_buffer, format="JPEG", quality=int(compression_rate * 100))
    return base64.b64encode(output_buffer.getvalue()).decode()

def format_images_markdown(images, prompt: str, preview: str="{image}?w=200&h=200") -> str:
    """
    Formats the given images as a markdown string.

    Args:
        images: The images to format.
        prompt (str): The prompt for the images.
        preview (str, optional): The preview URL format. Defaults to "{image}?w=200&h=200".

    Returns:
        str: The formatted markdown string.
    """
    if isinstance(images, list):
        images = [f"[![#{idx+1} {prompt}]({preview.replace('{image}', image)})]({image})" for idx, image in enumerate(images)]
        images = "\n".join(images)
    else:
        images = f"[![{prompt}]({images})]({images})"
    start_flag = "<!-- generated images start -->\n"
    end_flag = "<!-- generated images end -->\n"
    return f"\n{start_flag}{images}\n{end_flag}\n"

def to_bytes(image: Image.Image) -> bytes:
    """
    Converts the given image to bytes.

    Args:
        image (Image.Image): The image to convert.

    Returns:
        bytes: The image as bytes.
    """
    bytes_io = BytesIO()
    image.save(bytes_io, image.format)
    image.seek(0)
    return bytes_io.getvalue()

class ImageResponse():
    def __init__(
        self,
        images: Union[str, list],
        alt: str,
        options: dict = {}
    ):
        self.images = images
        self.alt = alt
        self.options = options
        
    def __str__(self) -> str:
        return format_images_markdown(self.images, self.alt)
    
    def get(self, key: str):
        return self.options.get(key)