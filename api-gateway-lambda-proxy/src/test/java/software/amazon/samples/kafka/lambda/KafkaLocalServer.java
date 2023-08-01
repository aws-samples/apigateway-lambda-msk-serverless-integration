// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

package software.amazon.samples.kafka.lambda;

import kafka.server.KafkaConfig;
import kafka.server.KafkaServer;
import org.apache.curator.test.TestingServer;
import org.apache.kafka.common.utils.Time;
import org.junit.rules.ExternalResource;
import scala.Some;

import java.io.File;
import java.io.IOException;

import java.util.Properties;

class KafkaLocalServer extends ExternalResource {

    private TestingServer testingServer;
    private KafkaServer kafka;
    private File tmpFolder;
    private int port;

    public KafkaLocalServer(File newFolder, int zookeeperPorts) {
        tmpFolder = newFolder;
        port = zookeeperPorts;
    }

    public void start() throws Exception {
        testingServer = new TestingServer(port, tmpFolder);
        testingServer.start();


        Properties props = new Properties();
        props.put("zookeeper.connect", testingServer.getConnectString());
        props.put("broker.id", "1");
        props.put("offsets.topic.replication.factor", "1");
        props.setProperty("log.dirs", tmpFolder.getPath());
        KafkaConfig kafkaConfig = new KafkaConfig(props);

        // List<KafkaMetricsReporter> metrics          = new ArrayList<>();
        // Buffer<KafkaMetricsReporter> metricsReporters = JavaConverters.asScala(metrics)


        kafka = new KafkaServer(kafkaConfig, Time.SYSTEM, new Some<String>("test-server"), false);
        kafka.startup();


    }

    public String getZookeeperConnectionString () {
        return testingServer.getConnectString().split(":")[0] + ":9092";
    }

    public void stop() throws IOException {
        kafka.shutdown();
        testingServer.stop();
        testingServer.close();
    }


}
