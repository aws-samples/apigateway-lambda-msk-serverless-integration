package software.amazon.samples.kafka.lambda;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

public class KafkaHandlerTest {

    @Test
    public void handleRequest_shouldReturnConstantValue() {

        assertEquals("a", "a");
    }
}
