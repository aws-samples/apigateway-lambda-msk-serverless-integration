// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
package software.amazon.samples.kafka.lambda;

import java.util.Map;
import java.util.Properties;

public class KafkaProducerPropertiesFactoryImpl implements KafkaProducerPropertiesFactory {

    private Properties kafkaProducerProperties;

    // Constructor for the KafkaProducerPropertiesFactoryImpl.
    public KafkaProducerPropertiesFactoryImpl() {

    }

    // This method retrieves the Kafka bootstrap server details from environment variables.
    private String getBootstrapServer() {
        return System.getenv("BOOTSTRAP_SERVER");
    }

    // This method returns Kafka Producer properties. If the properties were previously created, 
    // it returns the existing ones. Otherwise, it creates new properties.
    @Override
    public Properties getProducerProperties() {
        // If properties are already defined, return them.
        if (kafkaProducerProperties != null)
            return kafkaProducerProperties;

        // Definitions for serializers and callbacks to be used with Kafka Producer.
        String serializer = org.apache.kafka.common.serialization.StringSerializer.class.getCanonicalName();
        String callbackHandler = software.amazon.msk.auth.iam.IAMClientCallbackHandler.class.getCanonicalName();
        String loginModule = software.amazon.msk.auth.iam.IAMLoginModule.class.getCanonicalName();

        // Configuration map with necessary Kafka Producer properties. 
        // This includes serializers, bootstrap server details, security protocol, SASL mechanism, 
        // and JAAS config for SASL, callback handler, max idle time, and reconnect backoff time.
        Map<String, String> configuration = Map.of(
            "key.serializer", serializer, // Serializer class for key that implements the `org.apache.kafka.common.serialization.Serializer` interface.
            "value.serializer", serializer, // Serializer class for value that implements the `org.apache.kafka.common.serialization.Serializer` interface.
            "bootstrap.servers", getBootstrapServer(), // A list of host/port pairs to use for establishing the initial connection to the Kafka cluster.
            "security.protocol", "SASL_SSL", // Protocol used to communicate with brokers. SASL_SSL is the recommended setting for encryption and authentication.
            "sasl.mechanism", "AWS_MSK_IAM", // SASL mechanism used for client connections. This may be any mechanism for which a security provider is available.
            "sasl.jaas.config", loginModule+ " required;", // JAAS configuration settings. The format for the value is: '<loginModuleClass> <controlFlag> (<optionName>=<optionValue>)*;'. The IAMLoginModule class is used for AWS MSK IAM authentication.
            "sasl.client.callback.handler.class", callbackHandler, // The fully qualified name of a SASL client callback handler class that implements the AuthenticateCallbackHandler interface.
            "connections.max.idle.ms", "60", // Close idle connections after the number of milliseconds specified by this config.
            "reconnect.backoff.ms", "1000" // The amount of time to wait before attempting to reconnect to a given host when a connection fails. 
        );

        // Initializing the Kafka Producer Properties.
        kafkaProducerProperties = new Properties();

        // Populating the Kafka Producer Properties with the configuration map.
        for (Map.Entry<String, String> configEntry : configuration.entrySet()) {
            kafkaProducerProperties.put(configEntry.getKey(), configEntry.getValue());
        }

        // Return the configured Kafka Producer Properties.
        return kafkaProducerProperties;
    }

}
