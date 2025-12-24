from unittest.mock import MagicMock


def test_item_image_put_url(client, logged_in_user):
    """
    Test POST /api/v1/item/image-upload-url
    Should return putUrl and newFilename.
    """
    # Access the real app object to mock the S3 client
    app = client.application
    app.s3_client.generate_presigned_url = MagicMock(
        return_value="https://fake-s3-url.com/put"
    )

    response = client.post(
        "/api/item/image-upload-url",
        json={"filename": "test.jpg", "contentType": "image/jpeg"},
    )

    assert response.status_code == 200
    data = response.json
    assert data["putUrl"] == "https://fake-s3-url.com/put"
    assert "item_images/" in data["newFilename"]
    assert "test.jpg" in data["newFilename"]

    # Verify arguments called
    app.s3_client.generate_presigned_url.assert_called_once()
    args, kwargs = app.s3_client.generate_presigned_url.call_args
    assert args[0] == "put_object"
    assert kwargs["Params"]["ContentType"] == "image/jpeg"


def test_profile_image_put_url(client, logged_in_user):
    """
    Test POST /api/profile/image-upload-url
    """
    app = client.application
    app.s3_client.generate_presigned_url = MagicMock(
        return_value="https://fake-s3-url.com/profile-put"
    )

    response = client.post(
        "/api/profile/image-upload-url",
        json={"filename": "mypic.png", "contentType": "image/png"},
    )

    assert response.status_code == 200
    data = response.json
    assert data["putUrl"] == "https://fake-s3-url.com/profile-put"
    assert "profile_images/" in data["newFilename"]
    assert "mypic.png" in data["newFilename"]

    app.s3_client.generate_presigned_url.assert_called()
