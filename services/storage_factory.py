"""Storage factory for abstracting between local and S3 storage."""
import logging
from typing import Union
from config import settings

logger = logging.getLogger(__name__)


def get_storage_service() -> Union['StorageService', 'S3StorageService']:
    """
    Get storage service based on configuration.
    
    Returns:
        StorageService or S3StorageService based on STORAGE_TYPE setting
    """
    storage_type = getattr(settings, 'storage_type', 'local').lower()
    
    if storage_type == 's3':
        logger.info("Using S3 storage service")
        from services.s3_storage import get_s3_storage_service
        return get_s3_storage_service()
    else:
        logger.info("Using local storage service")
        from services.storage import get_storage_service as get_local_storage
        return get_local_storage()


# Convenience exports
__all__ = ['get_storage_service']
