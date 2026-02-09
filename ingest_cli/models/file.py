"""File metadata models for HxAI Ingestion API.

Models for representing file content metadata and upload references.
Used when documents include binary file attachments.
"""

from pydantic import BaseModel, ConfigDict, Field


class ContentMetadata(BaseModel):
    """File content metadata structure.

    Describes the file's size, name, MIME type, and optional digest.

    Example:
        {
            "size": 23100,
            "name": "document.pdf",
            "content-type": "application/pdf",
            "digest": "sha256:abc123..."
        }
    """

    model_config = ConfigDict(populate_by_name=True)

    size: int = Field(ge=0, description="File size in bytes")
    name: str = Field(min_length=1, description="Original filename")
    content_type: str = Field(
        alias="content-type",
        description="MIME type (pattern: ^[a-zA-Z-]+/[a-zA-Z0-9.+_-]+$)",
    )
    digest: str | None = Field(
        default=None,
        description="File hash digest (optional)",
    )


class FileUpload(BaseModel):
    """File upload reference (ID from presigned URL).

    References a file uploaded via the presigned URL endpoint.

    Example:
        {
            "id": "e381e783-1e30-4793-b250-3eda634b7c2c",
            "content-type": "application/pdf"
        }
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(min_length=1, description="Upload ID from presigned URL")
    content_type: str = Field(
        alias="content-type",
        description="MIME type of uploaded file",
    )


class FileMetadataOnly(BaseModel):
    """File metadata without upload (metadata-only events).

    Used when sending metadata updates without re-uploading the file.

    Example:
        {
            "content-metadata": {
                "size": 23100,
                "name": "document.pdf",
                "content-type": "application/pdf"
            }
        }
    """

    model_config = ConfigDict(populate_by_name=True)

    content_metadata: ContentMetadata = Field(alias="content-metadata")


class FileMetadataWithUpload(BaseModel):
    """File with both metadata and upload reference.

    Used when uploading a new file with complete metadata.
    Note: content-type is specified at BOTH file level AND inside content-metadata.

    Example:
        {
            "content-metadata": {...},
            "id": "uuid-from-presigned-url",
            "content-type": "application/pdf"
        }
    """

    model_config = ConfigDict(populate_by_name=True)

    content_metadata: ContentMetadata = Field(alias="content-metadata")
    id: str = Field(min_length=1, description="Upload ID from presigned URL")
    content_type: str = Field(
        alias="content-type",
        description="MIME type for the upload (must match content-metadata)",
    )


class FileProperty(BaseModel):
    """File property wrapper for content events.

    Wraps file information in the required 'file' structure.

    Example:
        {
            "file": {
                "id": "...",
                "content-type": "...",
                "content-metadata": {...}
            }
        }
    """

    model_config = ConfigDict(populate_by_name=True)

    file: FileMetadataWithUpload | FileUpload | FileMetadataOnly

    @classmethod
    def with_upload(
        cls,
        upload_id: str,
        content_type: str,
        size: int,
        name: str,
        digest: str | None = None,
    ) -> "FileProperty":
        """Create FileProperty with upload reference and metadata.

        Args:
            upload_id: ID returned from presigned URL endpoint
            content_type: MIME type of the file
            size: File size in bytes
            name: Original filename
            digest: Optional file hash

        Returns:
            FileProperty with complete upload information
        """
        return cls(
            file=FileMetadataWithUpload(
                **{  # type: ignore[arg-type]
                    "content-metadata": ContentMetadata(
                        size=size,
                        name=name,
                        **{"content-type": content_type},  # type: ignore[arg-type]
                        digest=digest,
                    ),
                    "content-type": content_type,
                },
                id=upload_id,
            )
        )

    @classmethod
    def upload_only(cls, upload_id: str, content_type: str) -> "FileProperty":
        """Create FileProperty with just upload reference.

        Args:
            upload_id: ID returned from presigned URL endpoint
            content_type: MIME type of the file

        Returns:
            FileProperty with upload ID only
        """
        return cls(file=FileUpload(id=upload_id, **{"content-type": content_type}))  # type: ignore[arg-type]

    @classmethod
    def metadata_only(
        cls,
        size: int,
        name: str,
        content_type: str,
        digest: str | None = None,
    ) -> "FileProperty":
        """Create FileProperty with metadata only (no upload).

        Args:
            size: File size in bytes
            name: Original filename
            content_type: MIME type of the file
            digest: Optional file hash

        Returns:
            FileProperty with metadata only
        """
        return cls(
            file=FileMetadataOnly(
                **{  # type: ignore[arg-type]
                    "content-metadata": ContentMetadata(
                        size=size,
                        name=name,
                        **{"content-type": content_type},  # type: ignore[arg-type]
                        digest=digest,
                    )
                }
            )
        )
