// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

package software.amazon.samples.kafka.lambda;

import java.util.Properties;

// This class implements KafkaHandlerPropertiesFactory and is responsible for creating and providing
// the properties needed to connect to the Kafka cluster using the provided bootstrap server.
public class KafkaHandlerPropertiesFactoryImpl implements KafkaHandlerPropertiesFactory {

    // The properties object that will hold the configuration settings for the Kafka Handler.
    private Properties kafkaHandlerProperties;

    public KafkaHandlerPropertiesFactoryImpl() {
    }

    // This method returns the Kafka Handler properties, and if they haven't been initialized yet,
    // it will create and configure them.
    @Override
    public Properties getHandlerProperties(String bootStrapServer) {
        // If the properties have already been initialized, return them
        if (kafkaHandlerProperties != null)
            return kafkaHandlerProperties;

        // Define the classes for the serializers and the callback handler
        String serializer = org.apache.kafka.common.serialization.StringSerializer.class.getCanonicalName();
        String callbackHandler = software.amazon.msk.auth.iam.IAMClientCallbackHandler.class.getCanonicalName();
        String loginModule = software.amazon.msk.auth.iam.IAMLoginModule.class.getCanonicalName();

        // Initialize the properties object
        kafkaHandlerProperties = new Properties();

        // Configure the properties for the Kafka Handler
        kafkaHandlerProperties.put("key.serializer", serializer); 
        // This property tells Kafka what serializer to use for message keys. A serializer is a class that converts 
        // objects into a byte array representation for transmission over network or storage on disk.

        kafkaHandlerProperties.put("value.serializer", serializer);
        // Similarly, this property tells Kafka what serializer to use for message values.

        kafkaHandlerProperties.put("bootstrap.servers", bootStrapServer); 
        // This property tells Kafka where to find the Kafka brokers that it needs to connect to. 
        // This is typically provided as a list of IP:port pairs.

        kafkaHandlerProperties.put("security.protocol", "SASL_SSL"); 
        // This property specifies the security protocol to be used for communication between the Kafka client 
        // and the Kafka broker. In this case, it's set to SASL_SSL, which means that it will use SASL (Simple 
        // Authentication and Security Layer) for authentication, and SSL (Secure Sockets Layer) for encryption.

        kafkaHandlerProperties.put("sasl.mechanism", "AWS_MSK_IAM"); 
        // This property tells Kafka which SASL mechanism to use. In this case, it's set to AWS_MSK_IAM, 
        // which means that it will use AWS's Managed Streaming for Kafka (MSK) IAM for authentication.

        kafkaHandlerProperties.put("sasl.jaas.config", loginModule+ " required;"); 
        // JAAS (Java Authentication and Authorization Service) config property for SASL clients which 
        // specify the login module and also other configurations.

        kafkaHandlerProperties.put("sasl.client.callback.handler.class", callbackHandler); 
        // The fully qualified name of a SASL client callback handler class that implements the AuthenticateCallbackHandler interface.

        kafkaHandlerProperties.put("connections.max.idle.ms", "60"); 
        // This property specifies the maximum amount of time in milliseconds that a connection can be idle 
        // before the client will disconnect from the broker.

        kafkaHandlerProperties.put("reconnect.backoff.ms", "1000"); 
        // This property determines the amount of time in milliseconds that the client will wait before attempting 
        // to reconnect to the broker after a connection failure.


        // Return the properties object
        return kafkaHandlerProperties;
    }
}
