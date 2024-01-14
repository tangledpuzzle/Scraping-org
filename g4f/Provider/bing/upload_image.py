"""
Module to handle image uploading and processing for Bing AI integrations.
"""

from __future__ import annotations
import string
import random
import json
import math
from aiohttp import ClientSession
from PIL import Image

from ...typing import ImageType, Tuple
from ...image import to_image, process_image, to_base64, ImageResponse

IMAGE_CONFIG = {
    "maxImagePixels": 360000,
    "imageCompressionRate": 0.7,
    "enableFaceBlurDebug": False,
}

async def upload_image(
    session: ClientSession, 
    image_data: ImageType, 
    tone: str, 
    proxy: str = None
) -> ImageResponse:
    """
    Uploads an image to Bing's AI service and returns the image response.

    Args:
        session (ClientSession): The active session.
        image_data (bytes): The image data to be uploaded.
        tone (str): The tone of the conversation.
        proxy (str, optional): Proxy if any. Defaults to None.

    Raises:
        RuntimeError: If the image upload fails.

    Returns:
        ImageResponse: The response from the image upload.
    """
    image = to_image(image_data)
    new_width, new_height = calculate_new_dimensions(image)
    processed_img = process_image(image, new_width, new_height)
    img_binary_data = to_base64(processed_img, IMAGE_CONFIG['imageCompressionRate'])

    data, boundary = build_image_upload_payload(img_binary_data, tone)
    headers = prepare_headers(session, boundary)

    async with session.post("https://www.bing.com/images/kblob", data=data, headers=headers, proxy=proxy) as response:
        if response.status != 200:
            raise RuntimeError("Failed to upload image.")
        return parse_image_response(await response.json())

def calculate_new_dimensions(image: Image.Image) -> Tuple[int, int]:
    """
    Calculates the new dimensions for the image based on the maximum allowed pixels.

    Args:
        image (Image): The PIL Image object.

    Returns:
        Tuple[int, int]: The new width and height for the image.
    """
    width, height = image.size
    max_image_pixels = IMAGE_CONFIG['maxImagePixels']
    if max_image_pixels / (width * height) < 1:
        scale_factor = math.sqrt(max_image_pixels / (width * height))
        return int(width * scale_factor), int(height * scale_factor)
    return width, height

def build_image_upload_payload(image_bin: str, tone: str) -> Tuple[str, str]:
    """
    Builds the payload for image uploading.

    Args:
        image_bin (str): Base64 encoded image binary data.
        tone (str): The tone of the conversation.

    Returns:
        Tuple[str, str]: The data and boundary for the payload.
    """
    boundary = "----WebKitFormBoundary" + ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    data = f"--{boundary}\r\n" \
           f"Content-Disposition: form-data; name=\"knowledgeRequest\"\r\n\r\n" \
           f"{json.dumps(build_knowledge_request(tone), ensure_ascii=False)}\r\n" \
           f"--{boundary}\r\n" \
           f"Content-Disposition: form-data; name=\"imageBase64\"\r\n\r\n" \
           f"{image_bin}\r\n" \
           f"--{boundary}--\r\n"
    return data, boundary

def build_knowledge_request(tone: str) -> dict:
    """
    Builds the knowledge request payload.

    Args:
        tone (str): The tone of the conversation.

    Returns:
        dict: The knowledge request payload.
    """
    return {
        'invokedSkills': ["ImageById"],
        'subscriptionId': "Bing.Chat.Multimodal",
        'invokedSkillsRequestData': {
            'enableFaceBlur': True
        },
        'convoData': {
            'convoid': "",
            'convotone': tone
        }
    }

def prepare_headers(session: ClientSession, boundary: str) -> dict:
    """
    Prepares the headers for the image upload request.

    Args:
        session (ClientSession): The active session.
        boundary (str): The boundary string for the multipart/form-data.

    Returns:
        dict: The headers for the request.
    """
    headers = session.headers.copy()
    headers["Content-Type"] = f'multipart/form-data; boundary={boundary}'
    headers["Referer"] = 'https://www.bing.com/search?q=Bing+AI&showconv=1&FORM=hpcodx'
    headers["Origin"] = 'https://www.bing.com'
    return headers

def parse_image_response(response: dict) -> ImageResponse:
    """
    Parses the response from the image upload.

    Args:
        response (dict): The response dictionary.

    Raises:
        RuntimeError: If parsing the image info fails.

    Returns:
        ImageResponse: The parsed image response.
    """
    if not response.get('blobId'):
        raise RuntimeError("Failed to parse image info.")

    result = {'bcid': response.get('blobId', ""), 'blurredBcid': response.get('processedBlobId', "")}
    result["imageUrl"] = f"https://www.bing.com/images/blob?bcid={result['blurredBcid'] or result['bcid']}"

    result['originalImageUrl'] = (
        f"https://www.bing.com/images/blob?bcid={result['blurredBcid']}"
        if IMAGE_CONFIG["enableFaceBlurDebug"] else
        f"https://www.bing.com/images/blob?bcid={result['bcid']}"
    )
    return ImageResponse(result["imageUrl"], "", result)