// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
package software.amazon.samples.kafka.lambda;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyRequestEvent;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyResponseEvent;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import software.amazon.lambda.powertools.logging.Logging;
import software.amazon.lambda.powertools.tracing.Tracing;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Future;

import static software.amazon.lambda.powertools.utilities.jmespath.Base64Function.decode;

// This class is part of the AWS samples package and specifically deals with Kafka integration in a Lambda function.
// It serves as a simple API Gateway to Kafka Proxy, accepting requests and forwarding them to a Kafka topic.
public class SimpleApiGatewayKafkaProxy implements RequestHandler<APIGatewayProxyRequestEvent, APIGatewayProxyResponseEvent> {

    // Specifies the name of the Kafka topic where the messages will be sent
    public final String TOPIC_NAME = System.getenv("TOPIC_NAME");

    // Logger instance for logging events of this class
    private static final Logger log = LogManager.getLogger(SimpleApiGatewayKafkaProxy.class);
    
    // Factory to create properties for Kafka Producer
    public KafkaProducerPropertiesFactory kafkaProducerProperties = new KafkaProducerPropertiesFactoryImpl();
    
    // Instance of KafkaProducer
    private KafkaProducer<String, String> producer;

    // Overridden method from the RequestHandler interface to handle incoming API Gateway proxy events
    @Override
    @Tracing
    @Logging(logEvent = true)
    public APIGatewayProxyResponseEvent handleRequest(APIGatewayProxyRequestEvent input, Context context) {
        
        // Creating a response object to send back 
        APIGatewayProxyResponseEvent response = createEmptyResponse();
        try {
            // Extracting the message from the request body
            String message = getMessageBody(input);

            // Create a Kafka producer
            KafkaProducer<String, String> producer = createProducer();

            // Creating a record with topic name, request ID as key and message as value 
            ProducerRecord<String, String> record = new ProducerRecord<String, String>(TOPIC_NAME, context.getAwsRequestId(), message);

            // Sending the record to Kafka topic and getting the metadata of the record
            Future<RecordMetadata> send = producer.send(record);
            producer.flush();

            // Retrieve metadata about the sent record
            RecordMetadata metadata = send.get();

            // Logging the partition where the message was sent
            log.info(String.format("Message was send to partition %s", metadata.partition()));

            // If the message was successfully sent, return a 200 status code
            return response.withStatusCode(200).withBody("Message successfully pushed to kafka");
        } catch (Exception e) {
            // In case of exception, log the error message and return a 500 status code
            log.error(e.getMessage(), e);
            return response.withBody(e.getMessage()).withStatusCode(500);
        }
    }

    // Creates a Kafka producer if it doesn't already exist
    @Tracing
    private KafkaProducer<String, String> createProducer() {
        if (producer == null) {
            log.info("Connecting to kafka cluster");
            producer = new KafkaProducer<String, String>(kafkaProducerProperties.getProducerProperties());
        }
        return producer;
    }

    // Extracts the message from the request body. If it's base64 encoded, it's decoded first.
    private String getMessageBody(APIGatewayProxyRequestEvent input) {
        String body = input.getBody();

        if (input.getIsBase64Encoded()) {
            body = decode(body);
        }
        return body;
    }

    // Creates an empty API Gateway proxy response event with predefined headers.
    private APIGatewayProxyResponseEvent createEmptyResponse() {
        Map<String, String> headers = new HashMap<>();
        headers.put("Content-Type", "application/json");
        headers.put("X-Custom-Header", "application/json");
        APIGatewayProxyResponseEvent response = new APIGatewayProxyResponseEvent().withHeaders(headers);
        return response;
    }
}
