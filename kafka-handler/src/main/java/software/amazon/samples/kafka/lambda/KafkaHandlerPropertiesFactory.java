// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
package software.amazon.samples.kafka.lambda;


import java.util.Properties;

public interface KafkaHandlerPropertiesFactory {

    Properties getHandlerProperties(String bootStrapServer);
}
