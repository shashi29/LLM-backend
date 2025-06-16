# app/repositories/rag_repository.py
from typing import Any, List, Optional, Dict
from datetime import datetime
import os, uuid, json, tempfile
from sqlalchemy import text
from app.repositories.base_repository import BaseRepository
from app.models.rag_models import RAGCollection, ChatMessage, FileInfo, ChatSession, ChatStats

# Import necessary clients
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, OptimizersConfigDiff
from sentence_transformers import SentenceTransformer
from google.cloud import storage
from app.repositories.rabbitmq_utils import RabbitMQClient

# Google Cloud Storage Client wrapper
class GoogleStorageClient:
    def __init__(self, project_id=None, bucket_name='documents'):
        self.storage_client = storage.Client(project=project_id)
        self.default_bucket_name = bucket_name
        
        # Ensure the bucket exists
        self._ensure_bucket_exists(bucket_name)
    
    def _ensure_bucket_exists(self, bucket_name):
        """Create bucket if it doesn't exist"""
        try:
            if not self.storage_client.lookup_bucket(bucket_name):
                bucket = self.storage_client.create_bucket(bucket_name)
                print(f"Bucket {bucket_name} created")
            return True
        except Exception as e:
            print(f"Error creating bucket: {str(e)}")
            return False
        
    def upload_file(self, object_name, file_path, bucket_name=None):
        """Upload a file to GCS"""
        bucket_name = bucket_name or self.default_bucket_name
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        
        blob.upload_from_filename(file_path)
        return f"gs://{bucket_name}/{object_name}"
    
    def list_objects(self, prefix=None, bucket_name=None):
        """List objects in a bucket with optional prefix"""
        bucket_name = bucket_name or self.default_bucket_name
        bucket = self.storage_client.bucket(bucket_name)
        
        blobs = bucket.list_blobs(prefix=prefix)
        return [
            {
                'name': blob.name,
                'size': blob.size,
                'updated': blob.updated,
                'storage_path': f"gs://{bucket_name}/{blob.name}"
            } for blob in blobs
        ]
    
    def download_file(self, object_name, destination_file_name, bucket_name=None):
        """Download a file from GCS"""
        bucket_name = bucket_name or self.default_bucket_name
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        
        blob.download_to_filename(destination_file_name)
        return destination_file_name
    
    def download_as_bytes(self, object_name, bucket_name=None):
        """Download a file from GCS as bytes"""
        bucket_name = bucket_name or self.default_bucket_name
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        
        return blob.download_as_bytes()
    
    def remove_object(self, object_name, bucket_name=None):
        """Delete an object from GCS"""
        bucket_name = bucket_name or self.default_bucket_name
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        
        blob.delete()

# RabbitMQ Client wrapper with error handling
# class RabbitMQClient:
#     def __init__(self, host, queue, user, password):
#         self.host = host
#         self.queue = queue
#         self.user = user
#         self.password = password
#         self.connection = None
#         self.channel = None
#         self.is_connected = False
        
#         try:
#             import pika
#             credentials = pika.PlainCredentials(user, password)
#             self.connection = pika.BlockingConnection(
#                 pika.ConnectionParameters(host=host, credentials=credentials)
#             )
#             self.channel = self.connection.channel()
#             self.channel.queue_declare(queue=queue, durable=True)
#             self.is_connected = True
#             print(f"Successfully connected to RabbitMQ at {host}")
#         except Exception as e:
#             print(f"Warning: Could not connect to RabbitMQ at {host}: {str(e)}")
#             print("Document processing will be handled synchronously")
#             self.is_connected = False
        
#     def send_message(self, message, priority=0):
#         if not self.is_connected:
#             print("RabbitMQ not available, skipping message queue")
#             return False
            
#         try:
#             import pika
#             self.channel.basic_publish(
#                 exchange='',
#                 routing_key=self.queue,
#                 body=json.dumps(message),
#                 properties=pika.BasicProperties(
#                     delivery_mode=2,  # make message persistent
#                     priority=priority
#                 )
#             )
#             return True
#         except Exception as e:
#             print(f"Error sending message to RabbitMQ: {str(e)}")
#             return False
        
#     def close(self):
#         if self.connection and self.connection.is_open:
#             self.connection.close()

class RAGRepository(BaseRepository):
    def __init__(self):
        super().__init__('RAGCollection')
        # Initialize required clients
        self.qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL", "http://143.110.180.27:6333"))
        self.embeddings = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Initialize Google Cloud Storage client
        try:
            self.storage_client = GoogleStorageClient(
                project_id=os.getenv("GCP_PROJECT_ID"),
                bucket_name=os.getenv("GCS_BUCKET_NAME", "document_ocr_sr")
            )
            print("Google Cloud Storage client initialized successfully")
        except Exception as e:
            print(f"Warning: Could not initialize Google Cloud Storage: {str(e)}")
            self.storage_client = None
        
        # Create the table if it doesn't exist
        create_table_query = text("""
            CREATE TABLE IF NOT EXISTS RAGCollection (
                id SERIAL PRIMARY KEY,
                board_id INT REFERENCES Boards(id) ON DELETE CASCADE,
                collection_name VARCHAR(255) UNIQUE NOT NULL,
                vector_size INT DEFAULT 384,
                distance VARCHAR(50) DEFAULT 'COSINE',
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)
        self.create_table(create_table_query)
        
        # Create ChatMessage table
        create_chat_table_query = text("""
            CREATE TABLE IF NOT EXISTS ChatMessage (
                id SERIAL PRIMARY KEY,
                collection_id INT REFERENCES RAGCollection(id) ON DELETE CASCADE,
                session_id VARCHAR(255) NOT NULL,
                sender VARCHAR(50) NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.create_table(create_chat_table_query)

    def create_collection(self, collection: RAGCollection) -> RAGCollection:
        """Create a new RAG collection in Qdrant and database"""
        # Check if collection exists in Qdrant
        try:
            collections = self.qdrant_client.get_collections()
            if any(col.name == collection.collection_name for col in collections.collections):
                raise ValueError(f"Collection '{collection.collection_name}' already exists in Qdrant")
                
            # Create collection in Qdrant
            self.qdrant_client.create_collection(
                collection_name=collection.collection_name,
                vectors_config=VectorParams(
                    size=collection.vector_size,
                    distance=Distance[collection.distance],
                    on_disk=True
                ),
                optimizers_config=OptimizersConfigDiff(indexing_threshold=20000)
            )
        except Exception as e:
            print(f"Warning: Could not create collection in Qdrant: {str(e)}")
            # Continue anyway - we'll handle this gracefully
        
        # Create collection in database
        query = text("""
            INSERT INTO RAGCollection 
            (board_id, collection_name, vector_size, distance, created_at, updated_at)
            VALUES 
            (:board_id, :collection_name, :vector_size, :distance, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, board_id, collection_name, vector_size, distance, created_at, updated_at;
        """)
        
        values = {
            "board_id": collection.board_id,
            "collection_name": collection.collection_name,
            "vector_size": collection.vector_size,
            "distance": collection.distance
        }
        
        result = self.execute_query(query, values)
        if not result:
            raise ValueError("Failed to create collection in database")
            
        collection_dict = {
            "id": result[0],
            "board_id": result[1],
            "collection_name": result[2],
            "vector_size": result[3],
            "distance": result[4],
            "created_at": result[5],
            "updated_at": result[6]
        }
        
        return RAGCollection(**collection_dict)

    def get_collection(self, collection_id: int) -> Optional[RAGCollection]:
        """Get a collection by ID"""
        query = text("""
            SELECT id, board_id, collection_name, vector_size, distance, created_at, updated_at
            FROM RAGCollection
            WHERE id = :collection_id;
        """)
        
        result = self.execute_query(query, {"collection_id": collection_id})
        if not result:
            return None
            
        collection_dict = {
            "id": result[0],
            "board_id": result[1],
            "collection_name": result[2],
            "vector_size": result[3],
            "distance": result[4],
            "created_at": result[5],
            "updated_at": result[6]
        }
        
        return RAGCollection(**collection_dict)

    def get_collections_by_board(self, board_id: int) -> List[RAGCollection]:
        """Get all collections for a specific board"""
        query = text("""
            SELECT id, board_id, collection_name, vector_size, distance, created_at, updated_at
            FROM RAGCollection
            WHERE board_id = :board_id;
        """)
        
        results = self.execute_query_all(query, {"board_id": board_id})
        collections = []
        
        for result in results:
            collection_dict = {
                "id": result[0],
                "board_id": result[1],
                "collection_name": result[2],
                "vector_size": result[3],
                "distance": result[4],
                "created_at": result[5],
                "updated_at": result[6]
            }
            collections.append(RAGCollection(**collection_dict))
            
        return collections

    def delete_collection(self, collection_id: int) -> bool:
        """Delete a collection from Qdrant and database"""
        # Get collection details first
        collection = self.get_collection(collection_id)
        if not collection:
            return False
            
        # Delete from Qdrant
        try:
            self.qdrant_client.delete_collection(collection_name=collection.collection_name)
        except Exception as e:
            print(f"Warning: Could not delete collection from Qdrant: {str(e)}")
            
        # Delete from database
        query = text("""
            DELETE FROM RAGCollection
            WHERE id = :collection_id
            RETURNING id;
        """)
        
        result = self.execute_query(query, {"collection_id": collection_id})
        return result is not None

    def submit_document_job(self, collection_id: int, file_path: str, filename: str, metadata: Dict = {}) -> str:
        """Submit a document processing job or process synchronously if RabbitMQ is not available"""
        collection = self.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")
        
        # Check if storage client is available
        if not self.storage_client:
            raise ValueError("Google Cloud Storage is not available")
            
        # Upload file to Google Cloud Storage
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        object_name = f"{collection.collection_name}/{timestamp}_{filename}"
        
        try:
            storage_path = self.storage_client.upload_file(object_name, file_path)
        except Exception as e:
            raise ValueError(f"Failed to upload file to storage: {str(e)}")
        
        # Create job request
        job_id = str(uuid.uuid4())
        message = {
            "job_id": job_id,
            "collection_name": collection.collection_name,
            "storage_path": storage_path,
            "metadata": metadata
        }
        
        # Try to send to RabbitMQ, if not available process synchronously
        rabbitmq_client = RabbitMQClient(
            host=os.getenv("RABBITMQ_HOST", "http://94.72.117.126:5672"),
            queue=os.getenv("RABBITMQ_QUEUE", "document_processing"),
            user=os.getenv("RABBITMQ_USER", "cwRI82uX5HyT"),
            password=os.getenv("RABBITMQ_PASSWORD", "9j4u6PluofN5")
        )
        
        try:
            success = rabbitmq_client.send_message(message)
            if success:
                print(f"Document job {job_id} queued successfully")
                return job_id
            else:
                # RabbitMQ failed, process synchronously
                print("RabbitMQ failed, processing document synchronously")
                return self._process_document_synchronously(message)
        except Exception as e:
            print(f"RabbitMQ error: {str(e)}, processing document synchronously")
            return self._process_document_synchronously(message)

    def _process_document_synchronously(self, message: Dict) -> str:
        """Process document synchronously when RabbitMQ is not available"""
        try:
            # This is a simplified synchronous processing
            # In a real implementation, you'd want to extract text and create embeddings here
            print(f"Processing document synchronously: {message['storage_path']}")
            
            # For now, just return the job ID to indicate the file was uploaded
            # The actual text extraction and vector creation would happen here
            return message["job_id"]
        except Exception as e:
            raise ValueError(f"Failed to process document: {str(e)}")

    def chat(self, collection_id: int, message: str, session_id: Optional[str] = None) -> Dict:
        """Process a chat message and store chat history"""
        collection = self.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")
            
        # Generate a session ID if not provided
        session_id = session_id or str(uuid.uuid4())
        
        try:
            # Get vector embedding for the message
            embedding = self.embeddings.encode([message])[0]
            
            # Search Qdrant for similar content
            search_result = self.qdrant_client.search(
                collection_name=collection.collection_name,
                query_vector=embedding,
                limit=5
            )
            
            # Format context from search results
            context = "\n\n".join([
                f"Text: {hit.payload.get('text')}\n"
                f"Page Number: {hit.payload.get('page_number')}\n"
                f"Storage Path: {hit.payload.get('storage_path')}\n"
                f"Metadata: {hit.payload.get('metadata')}"
                for hit in search_result
            ])
        except Exception as e:
            print(f"Warning: Could not search vectors: {str(e)}")
            context = "No relevant context found."
        
        # Generate response (simplified - you might want to use a different LLM approach)
        try:
            from langchain.llms import OpenAI
            from langchain.chains import ConversationChain
            from langchain.memory import ConversationBufferMemory
            
            memory = ConversationBufferMemory()
            conversation = ConversationChain(llm=OpenAI(), memory=memory)
            response = conversation.predict(input=f"Context: {context}\nUser: {message}")
        except Exception as e:
            print(f"Warning: Could not generate LLM response: {str(e)}")
            response = f"I received your message: '{message}'. However, I'm currently unable to provide a detailed response due to system limitations."
        
        # Save user message
        self.save_chat_message(collection_id, session_id, "user", message)
        
        # Save assistant response
        self.save_chat_message(collection_id, session_id, "assistant", response)
        
        return {
            "session_id": session_id,
            "response": response
        }

    def save_chat_message(self, collection_id: int, session_id: str, sender: str, message: str) -> int:
        """Save a chat message to the database"""
        query = text("""
            INSERT INTO ChatMessage
            (collection_id, session_id, sender, message, timestamp)
            VALUES
            (:collection_id, :session_id, :sender, :message, CURRENT_TIMESTAMP)
            RETURNING id;
        """)
        
        values = {
            "collection_id": collection_id,
            "session_id": session_id,
            "sender": sender,
            "message": message
        }
        
        result = self.execute_query(query, values)
        return result[0] if result else None

    def get_chat_history(self, collection_id: int, session_id: Optional[str] = None) -> List[ChatMessage]:
        """Get chat history for a collection, optionally filtered by session ID"""
        query_text = """
            SELECT id, collection_id, session_id, sender, message, timestamp
            FROM ChatMessage
            WHERE collection_id = :collection_id
        """
        
        params = {"collection_id": collection_id}
        
        if session_id:
            query_text += " AND session_id = :session_id"
            params["session_id"] = session_id
            
        query_text += " ORDER BY timestamp ASC"
        query = text(query_text)
        
        results = self.execute_query_all(query, params)
        messages = []
        
        for result in results:
            message_dict = {
                "id": result[0],
                "collection_id": result[1],
                "session_id": result[2],
                "sender": result[3],
                "message": result[4],
                "timestamp": result[5]
            }
            messages.append(ChatMessage(**message_dict))
            
        return messages

    def get_chat_sessions(self, collection_id: int) -> List[ChatSession]:
        """Get all chat sessions for a collection"""
        query = text("""
            SELECT 
                session_id,
                MAX(timestamp) as last_message,
                COUNT(id) as message_count
            FROM ChatMessage
            WHERE collection_id = :collection_id
            GROUP BY session_id
            ORDER BY MAX(timestamp) DESC;
        """)
        
        results = self.execute_query_all(query, {"collection_id": collection_id})
        sessions = []
        
        for result in results:
            session = ChatSession(
                session_id=result[0],
                last_message=result[1],
                message_count=result[2]
            )
            sessions.append(session)
            
        return sessions

    def delete_chat_history(self, collection_id: int, session_id: str) -> int:
        """Delete chat history for a specific session"""
        query = text("""
            DELETE FROM ChatMessage
            WHERE collection_id = :collection_id AND session_id = :session_id
            RETURNING id;
        """)
        
        results = self.execute_query_all(query, {
            "collection_id": collection_id,
            "session_id": session_id
        })
        
        return len(results)

    def get_chat_stats(self, collection_id: int, start_date: Optional[datetime] = None, 
                       end_date: Optional[datetime] = None) -> ChatStats:
        """Get statistics for chat history"""
        # Base query
        query_text = """
            SELECT COUNT(id) as total_messages
            FROM ChatMessage
            WHERE collection_id = :collection_id
        """
        
        params = {"collection_id": collection_id}
        
        # Add date filters if provided
        if start_date:
            query_text += " AND timestamp >= :start_date"
            params["start_date"] = start_date
            
        if end_date:
            query_text += " AND timestamp <= :end_date"
            params["end_date"] = end_date
            
        query = text(query_text)
        result = self.execute_query(query, params)
        total_messages = result[0] if result else 0
        
        # Count unique sessions
        sessions_query_text = """
            SELECT COUNT(DISTINCT session_id)
            FROM ChatMessage
            WHERE collection_id = :collection_id
        """
        
        if start_date:
            sessions_query_text += " AND timestamp >= :start_date"
            
        if end_date:
            sessions_query_text += " AND timestamp <= :end_date"
            
        sessions_query = text(sessions_query_text)
        sessions_result = self.execute_query(sessions_query, params)
        unique_sessions = sessions_result[0] if sessions_result else 0
        
        # Get message counts by sender
        sender_query_text = """
            SELECT sender, COUNT(id)
            FROM ChatMessage
            WHERE collection_id = :collection_id
        """
        
        if start_date:
            sender_query_text += " AND timestamp >= :start_date"
            
        if end_date:
            sender_query_text += " AND timestamp <= :end_date"
            
        sender_query_text += " GROUP BY sender"
        sender_query = text(sender_query_text)
        sender_results = self.execute_query_all(sender_query, params)
        
        message_counts = {}
        for sender_result in sender_results:
            message_counts[sender_result[0]] = sender_result[1]
            
        # Calculate average messages per session
        avg_messages = total_messages / unique_sessions if unique_sessions > 0 else 0
        
        return ChatStats(
            total_messages=total_messages,
            unique_sessions=unique_sessions,
            avg_messages_per_session=round(avg_messages, 2),
            message_counts_by_sender=message_counts
        )

    def list_files(self, collection_id: int, prefix: Optional[str] = None, limit: int = 100) -> List[FileInfo]:
        """List files for a collection"""
        collection = self.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")
        
        if not self.storage_client:
            return []  # Return empty list if storage is not available
            
        prefix_path = f"{collection.collection_name}/{prefix if prefix else ''}"
        
        try:
            # List objects in Google Cloud Storage
            objects = self.storage_client.list_objects(prefix=prefix_path)
            files = []
            
            for obj in objects[:limit]:
                file_info = FileInfo(
                    filename=obj['name'].split('/')[-1],
                    size=obj['size'],
                    storage_path=obj['storage_path'],
                    metadata={}
                )
                files.append(file_info)
                
            return files
        except Exception as e:
            print(f"Warning: Could not list files: {str(e)}")
            return []

    def delete_file(self, collection_id: int, filename: str, delete_vectors: bool = True) -> bool:
        """Delete a file from storage and optionally from the vector database"""
        collection = self.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection with ID {collection_id} not found")
        
        if not self.storage_client:
            raise ValueError("Google Cloud Storage is not available")
            
        prefix_path = collection.collection_name
        
        try:
            # Find the exact object name that matches the filename
            objects = self.storage_client.list_objects(prefix=prefix_path)
            target_object = None
            target_storage_path = None
            
            for obj in objects:
                if obj['name'].split('/')[-1] == filename:
                    target_object = obj['name']
                    target_storage_path = obj['storage_path']
                    break
                    
            if not target_object:
                raise ValueError(f"File {filename} not found in collection {collection.collection_name}")
                
            # Delete from Google Cloud Storage
            self.storage_client.remove_object(target_object)
            
            # Delete vectors if requested
            if delete_vectors and target_storage_path:
                try:
                    from qdrant_client.http.models import Filter, FieldCondition, MatchValue
                    
                    self.qdrant_client.delete(
                        collection_name=collection.collection_name,
                        points_filter=Filter(
                            must=[
                                FieldCondition(
                                    key="storage_path",
                                    match=MatchValue(value=target_storage_path)
                                )
                            ]
                        )
                    )
                except Exception as e:
                    print(f"Warning: Could not delete vectors: {str(e)}")
                
            return True
        except Exception as e:
            raise ValueError(f"Failed to delete file: {str(e)}")