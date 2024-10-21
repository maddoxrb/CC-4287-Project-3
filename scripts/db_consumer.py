# db_consumer.py
#
# Author: Team 14 (Maddox, Emma, Abhay)
# CS4287-5287: Principles of Cloud Computing, Vanderbilt University
#
#
# Purpose: db consumer file pulls image and inference data from kafka topics 'inferences' and 'iot-images'
# and inserts them into the mongodb database 'iot_database'


import json
from kafka import KafkaConsumer
from pymongo import MongoClient
import base64

# Kafka Consumer Configuration for both topics
consumer = KafkaConsumer(
    'iot-images', 'inferences', 
    bootstrap_servers='192.168.5.241:9092', 
    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
)


mongo_client = MongoClient('mongodb://192.168.5.4:27017')

db = mongo_client['iot_database'] 
collection = db['images'] 


pending_inferences = {}

# Start consuming messages from Kafka
for msg in consumer:
    message = msg.value
    topic = msg.topic

    if topic == 'iot-images':
        image_id = message['ID']
        ground_truth = message['GroundTruth']
        image_data = message['Data'].encode('latin1')

        image_base64 = base64.b64encode(image_data).decode('utf-8')

        # Check if inference already exists for this image
        if image_id in pending_inferences:
            document = {
                'ID': image_id,
                'GroundTruth': ground_truth,
                'Data': image_base64,  
                'InferredValue': pending_inferences.pop(image_id)
            }
            collection.insert_one(document)
            print(f"Stored image {image_id} with ground truth '{ground_truth}' and inference into MongoDB") 
        else:

            # Store image data without inference
            document = {
                'ID': image_id,
                'GroundTruth': ground_truth,
                'Data': image_base64,  
                'InferredValue': None 
            }
            collection.insert_one(document)
            print(f"Stored image {image_id} with ground truth '{ground_truth}' into MongoDB")

    elif topic == 'inferences':
        image_id = message['ID']
        inferred_value = message['InferredValue']


        result = collection.find_one({'ID': image_id})

        if result:
            collection.update_one({'ID': image_id}, {'$set': {'InferredValue': inferred_value}})
            print(f"Updated image {image_id} with inferred value '{inferred_value}' in MongoDB")
        else:
            pending_inferences[image_id] = inferred_value

consumer.close()
mongo_client.close()
