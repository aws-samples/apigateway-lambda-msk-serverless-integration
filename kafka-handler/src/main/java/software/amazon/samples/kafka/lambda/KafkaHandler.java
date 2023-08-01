package software.amazon.samples.kafka.lambda;

import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Collections;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.LambdaLogger;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.events.CloudFormationCustomResourceEvent;
import software.amazon.awssdk.http.urlconnection.UrlConnectionHttpClient;
import software.amazon.awssdk.services.kafka.KafkaClient;
import software.amazon.awssdk.services.kafka.model.GetBootstrapBrokersRequest;
import software.amazon.awssdk.services.kafka.model.GetBootstrapBrokersResponse;
import software.amazon.awssdk.regions.Region;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.admin.ListTopicsResult;
import org.json.JSONObject;



//The KafkaHandler class in the software.amazon.samples.kafka.lambda package is a custom AWS Lambda function handler that interacts
// with an Amazon MSK (Managed Streaming for Apache Kafka) cluster. 
//This class handles CloudFormation custom resource requests, allowing for creation, deletion, and management of Kafka topics, and 
//communicates the results back to the AWS CloudFormation service (incl. BootstrapServerEndpoints)
public class KafkaHandler  implements RequestHandler<CloudFormationCustomResourceEvent, Object> { 
    // The Kafka client used for communication
    private final KafkaClient kafkaClient;
    // The Amazon Resource Name (ARN) of the Amazon MSK cluster
    private final String clusterArn = System.getenv("MSK_CLUSTER_ARN");
    // Factory to obtain the Kafka Handler properties
    public KafkaHandlerPropertiesFactory kafkaHandlerProperties = new KafkaHandlerPropertiesFactoryImpl();
    // The response body for the CloudFormation custom resource for the CFN response    
    public JSONObject cfnResponseBody = new JSONObject();

    // KafkaHandler constructor
    public KafkaHandler() {
        this.kafkaClient = KafkaClient.builder()
                .httpClientBuilder(UrlConnectionHttpClient.builder())
                .region(Region.EU_CENTRAL_1)
                .build();
    }

    // Connects to the Kafka cluster using the bootstrap servers provided
    private AdminClient connectToKafka(String bootstrapServers) {
        return AdminClient.create(kafkaHandlerProperties.getHandlerProperties(bootstrapServers));
    }

    // Checks if a topic exists on the Kafka cluster
    private boolean topicExists(AdminClient adminClient, String topicName) {
        try {
            ListTopicsResult listTopicsResult = adminClient.listTopics();
            Set<String> topics = listTopicsResult.names().get();
            return topics.contains(topicName);
        } catch (InterruptedException | ExecutionException e) {
            // Log or handle exception as required
            throw new RuntimeException("Failed to check topic existence.", e);
        }
    }

    // Retrieves the bootstrap servers for the Kafka cluster specified by the ARN
    private String getBootstrapServers(String clusterArn) {
        GetBootstrapBrokersResponse response = kafkaClient.getBootstrapBrokers(GetBootstrapBrokersRequest.builder().clusterArn(clusterArn).build());
        System.out.println(response.toString());
        return response.bootstrapBrokerStringSaslIam();
    }

    // Handles a request from AWS Lambda function
    @Override
    public Object handleRequest(CloudFormationCustomResourceEvent input, Context context) {
        // Fetches the logger instance from the lambda context
        LambdaLogger logger = context.getLogger();
        // Logs the input event data
        logger.log("Input: " + input);

        // Extracts the request type from the input event
        final String requestType = input.getRequestType();

        // Initializes an ExecutorService for concurrent execution
        ExecutorService service = Executors.newSingleThreadExecutor();
        // Initializes a JSONObject to store response data
        JSONObject responseData = new JSONObject();
        try {
            // Checks if the request type is null, throws exception if true
            if (requestType == null) {
                throw new RuntimeException();
            }
            // Runnable task definition
            Runnable r = () -> {
                // Gets the bootstrap servers for the Kafka cluster
                final String bootstrapServers = getBootstrapServers(clusterArn);
                // Adds bootstrap servers info to the response data
                responseData.put("BootstrapServers", bootstrapServers);
                
                // Connects to the Kafka cluster
                final AdminClient adminClient = connectToKafka(bootstrapServers);
                
                // Logs resource properties
                logger.log("Resource Properties: " + input.getResourceProperties().toString());

                // Fetches resource properties from the input event
                Map<String, Object> resourceProperties = input.getResourceProperties();

                // Fetches topic configuration from the resource properties
                Object topicConfigObject = resourceProperties.get("topicConfig");

                // Checks if the topic configuration is of type Map, throws exception if not
                if (!(topicConfigObject instanceof Map)) {
                    throw new ClassCastException("The value for topicConfig in resourceProperties is not a Map.");
                }

                // Converts topicConfigObject to a Map of String, String
                Map<String, String> topicConfig = null;

                try {
                    topicConfig = (Map<String, String>) topicConfigObject;
                } catch (ClassCastException e) {
                    throw new ClassCastException("The value for topicConfig in resourceProperties is not a Map<String, String>.");
                }

                // Fetches topic name, number of partitions and replication factor from the topic configuration
                String topicName = topicConfig.get("topicName");
                int numPartitions = Integer.parseInt(topicConfig.get("numPartitions"));
                short replicationFactor = Short.parseShort(topicConfig.get("replicationFactor"));           
                
                // Processes different types of requests ("Create", "Update", "Delete", etc.)
                switch (requestType) {
                    // Code for handling "Update" and "Create" requests
                    case "Update":
                    case "Create": {
                        // Logs that we entered "Create" flow
                        logger.log("Entered Create Flow...");
                        // Checks if the topic already exists
                        if (!topicExists(adminClient, topicName)) {
                            // Code to handle the creation of a new topic
                            // Logs about topic creation
                            logger.log("Creating topic: " + topicName + " with numPartitions: " + numPartitions + " and replicationFactor: " + replicationFactor);
                            try {
                                // Code for creating a topic
                                adminClient.createTopics(Collections.singleton(new NewTopic(topicName, numPartitions, replicationFactor))).all().get();
                                // Sends a successful response if topic creation is successful
                                responseData.put("Message", "Resource creation successful!");
                                sendResponse(input, context, "SUCCESS", responseData);
                            // Logs exceptions and sends a failure response
                            } catch (Exception e) {
                                // Logs the exception class name and its message
                                logger.log(e.getClass().getSimpleName() + ": " + e.toString());
                                e.printStackTrace();
                                // Adds the exception details to the response data
                                responseData.put("Error", e.getClass().getSimpleName() + ": " + e.getStackTrace().toString());
                                // Sends a failure response
                                sendResponse(input, context, "FAILED", responseData);
                            }
                            break;
                        } else {
                            // Sends a successful response if the topic already exists                            
                            responseData.put("Message", "Topic " + topicName + "already exists!");
                            sendResponse(input, context, "SUCCESS", responseData);                           
                        }
                    }
                    // Code for handling "Delete" request
                    case "Delete": {
                        // Logs that we entered "Delete" flow
                        logger.log("Entered Delete Flow...");          
                        // Logs about topic deletion
                        logger.log("Deleting topic: " + topicName);
                        try {
                            // Code for deleting a topic
                            adminClient.deleteTopics(Collections.singleton(topicName)).all().get();
                            // Sends a successful response if topic deletion is successful     
                            responseData.put("Message", "Resource deletion successful!");
                            sendResponse(input, context, "SUCCESS", responseData);
                             // Logs exceptions and sends a failure response
                        } catch (Exception e) {
                                // Logs the exception class name and its message
                                logger.log(e.getClass().getSimpleName() + ": " + e.toString());
                                e.printStackTrace();
                                // Adds the exception details to the response data
                                responseData.put("Error", e.getClass().getSimpleName() + ": " + e.getStackTrace().toString());
                                // Sends a failure response
                                sendResponse(input, context, "FAILED", responseData);
                            }
                        break;
                    }
                    // Code for handling unknown request types
                    default: {
                        // Logs that we entered the default flow and sends a failure response
                        logger.log("Entered Default Flow...");
                        logger.log("FAILURE default case! RequestType: " + requestType + " is not supported");
                        sendResponse(input, context, "FAILED", responseData);
                        
                    }
                }
            };
            // Submits the task for execution and waits for it to finish with a timeout
            Future<?> f = service.submit(r);
            f.get(context.getRemainingTimeInMillis() - 1000, TimeUnit.MILLISECONDS);
        // Logs exceptions and sends a failure response
        } catch (final TimeoutException | InterruptedException | ExecutionException e) {

            logger.log("FAILURE!");
            sendResponse(input, context, "FAILED", responseData);
        } finally {
            // Shuts down the ExecutorServic
            service.shutdown();
        }
        // Wait for 3 seconds to avoid race conditions and ensure the result sent to CloudFormation can be processed
        try {
            Thread.sleep(3000);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        // Returns the response body as Lambda result
        return cfnResponseBody.toString();
    }
    

    // This function is responsible for sending a response back to a custom resource request
    public final Object sendResponse(
            final CloudFormationCustomResourceEvent input, // An AWS CloudFormation event data
            final Context context, // Context provided by the AWS Lambda environment
            final String responseStatus, // Status of the response, such as 'SUCCESS' or 'FAILED'
            JSONObject responseData) { // Data to be included in the response

        // Retrieve the URL for sending the response
        String responseUrl = input.getResponseUrl();
        // Log the response URL
        context.getLogger().log("ResponseURL: " + responseUrl);

        // Initialize the JSON object to hold the response body
        JSONObject responseBody = new JSONObject();
        URL url;

        try {
            // Create a URL object from the response URL
            url = new URL(responseUrl);

            // Open a connection to the URL
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            // Set the connection to allow output
            connection.setDoOutput(true);
            // Set the HTTP request method to PUT
            connection.setRequestMethod("PUT");

            // Populate the response body
            responseBody.put("Status", responseStatus);
            responseBody.put("PhysicalResourceId", context.getLogStreamName());
            responseBody.put("StackId", input.getStackId());
            responseBody.put("RequestId", input.getRequestId());
            responseBody.put("LogicalResourceId", input.getLogicalResourceId());
            responseBody.put("Data", responseData);

            // Log the response body that will be sent back to the custom resource
            context.getLogger().log("Sending following response back to custom resource: " + responseBody.toString());

            // Open an output stream writer to the URL connection
            OutputStreamWriter response = new OutputStreamWriter(connection.getOutputStream());
            // Write the response body to the output stream
            response.write(responseBody.toString());
            // Close the output stream
            response.close();

            // Store the response body for later use
            cfnResponseBody = responseBody;

            // Log the HTTP response code received from the custom resource
            context.getLogger().log("Response Code from custom resource: " + connection.getResponseCode());

        } catch (Exception e) {
            // Log any exceptions that occur during the response sending process
            context.getLogger().log("Exception during sending response back to custom resource: " + e.getStackTrace().toString());
        }

        // The function returns null because it doesn't need to return a result
        return null;
    }
}
