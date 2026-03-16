import logging
import os
import json
from typing import Any, Dict, Optional

from google.cloud import secretmanager
from google.cloud import storage
from google.cloud import firestore
from google.cloud import pubsub_v1
from google.cloud import logging as cloud_logging
import redis

logger = logging.getLogger("visionguide.cloud")

class CloudManager:
    _instance = None
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "project-017f83aa-1166-4bbf-aae")
    REDIS_HOST = os.getenv("Memorystore", "localhost")

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "project-017f83aa-1166-4bbf-aae")
            self.REDIS_HOST = os.getenv("Memorystore", "localhost")
            self.DATABASE_ID = os.getenv("FIRESTORE_DATABASE_ID")
            try:
                self.secret_client = secretmanager.SecretManagerServiceClient()
                self.storage_client = storage.Client(project=self.PROJECT_ID)
                self.firestore_client = firestore.Client(
                    project=self.PROJECT_ID, 
                    database=self.DATABASE_ID
                )
                self.publisher = pubsub_v1.PublisherClient()
                
                # Initialize Redis (Memorystore) Cache
                try:
                    self.redis_client = redis.Redis(host=self.REDIS_HOST, port=6379, db=0, socket_timeout=5)
                    logger.info(f"Memorystore (Redis) initialized at {self.REDIS_HOST}")
                except Exception as re:
                    logger.warning(f"Could not initialize Memorystore cache: {re}")
                    self.redis_client = None

                # Setup Cloud Logging
                self.logging_client = cloud_logging.Client(project=self.PROJECT_ID)
                logger.info("GCP Cloud Logging initialized.")
            except Exception as e:
                logger.warning(f"Failed to initialize some GCP clients: {e}")
            self.initialized = True

    def get_secret(self, secret_id: str, version_id: str = "latest") -> Optional[str]:
        """Fetch a secret from GCP Secret Manager with enhanced logging."""
        try:
            name = f"projects/{self.PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
            logger.info(f"Fetching secret: {name}")
            response = self.secret_client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.warning(f"Secret {secret_id} not available in GCP: {e}")
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

    def save_session(self, session_id: str, data: Dict[str, Any]):
        """Save session state to Redis (cache) and Firestore (persistence)."""
        try:
            # 1. Update High-Speed Cache (Redis)
            if self.redis_client:
                try:
                    self.redis_client.setex(
                        f"session:{session_id}",
                        3600,  # 1 hour TTL
                        json.dumps(data)
                    )
                    logger.info(f"Session {session_id} cached in Memorystore.")
                except Exception as re:
                    logger.warning(f"Failed to cache session {session_id} in Redis: {re}")

            # 2. Update Persistent Store (Firestore)
            doc_ref = self.firestore_client.collection("omnisense").document(session_id)
            doc_ref.set(data, merge=True)
            logger.info(f"Session {session_id} persisted in Firestore.")
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session state using Cache-Aside pattern (Redis -> Firestore)."""
        try:
            # 1. Try High-Speed Cache (Redis)
            if self.redis_client:
                try:
                    cached_data = self.redis_client.get(f"session:{session_id}")
                    if cached_data:
                        logger.info(f"Session {session_id} retrieved from Memorystore.")
                        return json.loads(cached_data)
                except Exception as re:
                    logger.warning(f"Redis fetch failed for session {session_id}: {re}")

            # 2. Fallback to Persistent Store (Firestore)
            doc_ref = self.firestore_client.collection("omnisense").document(session_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                # 3. Prime the Cache for next time
                if self.redis_client:
                    try:
                        self.redis_client.setex(f"session:{session_id}", 3600, json.dumps(data))
                        logger.info(f"Cache primed for session {session_id}.")
                    except:
                        pass
                return data
            return None
        except Exception as e:
            logger.error(f"Failed to fetch session {session_id}: {e}")
            return None

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
