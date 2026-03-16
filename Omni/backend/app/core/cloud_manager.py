import logging
import os
import json
from typing import Any, Dict, Optional

from google.cloud import secretmanager
from google.cloud import storage
from google.cloud import firestore
from google.cloud import pubsub_v1
from google.cloud import logging as cloud_logging

logger = logging.getLogger("visionguide.cloud")

class CloudManager:
    _instance = None
    PROJECT_ID = "multisensoryagent"

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.PROJECT_ID = "multisensoryagent"
            try:
                self.secret_client = secretmanager.SecretManagerServiceClient()
                self.storage_client = storage.Client(project=self.PROJECT_ID)
                self.firestore_client = firestore.Client(project=self.PROJECT_ID)
                self.publisher = pubsub_v1.PublisherClient()
                
                # Setup Cloud Logging
                self.logging_client = cloud_logging.Client(project=self.PROJECT_ID)
                # self.logging_client.setup_logging()
                logger.info("GCP Cloud Logging initialized (setup_logging disabled for debugging).")
            except Exception as e:
                logger.warning(f"Failed to initialize some GCP clients: {e}")
            self.initialized = True

    def get_secret(self, secret_id: str, version_id: str = "latest") -> Optional[str]:
        """Fetch a secret from GCP Secret Manager."""
        try:
            name = f"projects/{self.PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
            response = self.secret_client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Failed to fetch secret {secret_id}: {e}")
            return None

    def upload_blob(self, bucket_name: str, source_data: bytes, destination_blob_name: str, content_type: str = "image/jpeg"):
        """Uploads data to a GCS bucket."""
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_string(source_data, content_type=content_type)
            logger.info(f"File uploaded to {bucket_name}/{destination_blob_name}.")
            return blob.public_url
        except Exception as e:
            logger.error(f"Failed to upload to GCS: {e}")
            return None

    def save_user_preference(self, user_id: str, preferences: Dict[str, Any]):
        """Save user preferences to Firestore."""
        try:
            doc_ref = self.firestore_client.collection("user_preferences").document(user_id)
            doc_ref.set(preferences, merge=True)
            logger.info(f"Preferences saved for user {user_id}.")
        except Exception as e:
            logger.error(f"Failed to save preferences to Firestore: {e}")

    def publish_alert(self, topic_id: str, data: Dict[str, Any]):
        """Publish an alert message to a Pub/Sub topic."""
        try:
            topic_path = self.publisher.topic_path(self.PROJECT_ID, topic_id)
            message_json = json.dumps(data)
            message_bytes = message_json.encode("utf-8")
            future = self.publisher.publish(topic_path, data=message_bytes)
            logger.info(f"Message published to {topic_id}: {future.result()}")
        except Exception as e:
            logger.error(f"Failed to publish to Pub/Sub: {e}")

cloud_manager = CloudManager()
