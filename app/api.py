"""Contains Flask Blueprint for all routes related to API features. Each route returns some JSON that JavaScript can consume in a browser."""

from flask import (
    Blueprint,
    request,
    current_app,
)
from flask_login import login_required
from werkzeug.utils import secure_filename
from datetime import datetime

api = Blueprint("api", __name__, url_prefix="/v1")


@api.route("/item/image-upload-url", methods=["POST"])
@login_required
def item_image_put_url():
    filename = request.json["filename"]
    content_type = request.json["contentType"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"item_images/{timestamp}_{secure_filename(filename)}"
    put_url = get_put_url(new_filename, content_type)
    return {"putUrl": put_url, "newFilename": new_filename}


@api.route("/profile/image-upload-url", methods=["POST"])
@login_required
def profile_image_put_url():
    filename = request.json["filename"]
    content_type = request.json["contentType"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"profile_images/{timestamp}_{secure_filename(filename)}"
    put_url = get_put_url(new_filename, content_type)
    return {"putUrl": put_url, "newFilename": new_filename}


def get_put_url(filename: str, content_type: str):
    """
    Helper method for generating the presigned PUT url for uploading a given image to the app's R2 storage bucket

    Params
    ------
    filename: str
        The name of the file to be uploaded included the full path from the bucket root.

    content_type: str
        The MIME type of the file.
    """
    put_url = current_app.s3_client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": current_app.s3_bucket_id,
            "Key": filename,
            "ContentType": content_type,
        },
        ExpiresIn=3600,
    )
    return put_url
