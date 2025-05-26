// Architecture Summary:
// ----------------------
// - Kafka Topic: video_view_events (partitioned by videoId)
// - Flink Cluster: Multiple parallel Flink jobs (sharded by videoId hash)
// - Redis Cluster:
//     - Each Flink shard writes Top-K per videoId to a centralized Redis instance
//     - Redis keys: topk:{videoId}:{window} e.g. topk:abc123:1h
// - Global Aggregator Service:
//     - Periodically scans Redis keys across videoIds and merges Top-K into global Top-K

// Assumptions:
// - Events are JSON: {"videoId": "abc123", "userId": "xyz789", "timestamp": 1689990000}
// - K = 10

import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.functions.AggregateFunction;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.sink.SinkFunction;
import org.apache.flink.streaming.api.windowing.assigners.SlidingEventTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaConsumer;
import org.json.JSONObject;
import redis.clients.jedis.Jedis;

import java.time.Duration;
import java.util.*;

public class VideoTopKJob {

    public static void main(String[] args) throws Exception {
        final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.enableCheckpointing(60000);

        Properties props = new Properties();
        props.setProperty("bootstrap.servers", "localhost:9092");
        props.setProperty("group.id", "video-topk-group");

        DataStream<String> stream = env.addSource(
                new FlinkKafkaConsumer<>("video_view_events", new SimpleStringSchema(), props)
        );

        DataStream<Tuple2<String, String>> parsed = stream.map(line -> {
            JSONObject json = new JSONObject(line);
            return new Tuple2<>(json.getString("videoId"), json.getString("userId"));
        }).returns(Tuple2.class);

        parsed
            .assignTimestampsAndWatermarks(
                WatermarkStrategy.<Tuple2<String, String>>forBoundedOutOfOrderness(Duration.ofSeconds(10))
                        .withTimestampAssigner((e, ts) -> System.currentTimeMillis())
            )
            .keyBy(t -> t.f0) // key by videoId
            .window(SlidingEventTimeWindows.of(Time.hours(1), Time.minutes(5)))
            .aggregate(new CountUsers(), new RedisTopKWindowSink("1h"));

        env.execute("Per-Video Top-K Views Job");
    }

    public static class CountUsers implements AggregateFunction<Tuple2<String, String>, Map<String, Integer>, Map<String, Integer>> {
        @Override
        public Map<String, Integer> createAccumulator() {
            return new HashMap<>();
        }

        @Override
        public Map<String, Integer> add(Tuple2<String, String> value, Map<String, Integer> acc) {
            acc.put(value.f1, acc.getOrDefault(value.f1, 0) + 1);
            return acc;
        }

        @Override
        public Map<String, Integer> getResult(Map<String, Integer> acc) {
            return acc;
        }

        @Override
        public Map<String, Integer> merge(Map<String, Integer> a, Map<String, Integer> b) {
            b.forEach((k, v) -> a.merge(k, v, Integer::sum));
            return a;
        }
    }

    public static class RedisTopKWindowSink implements SinkFunction<Map<String, Integer>> {
        private final String windowLabel;

        public RedisTopKWindowSink(String windowLabel) {
            this.windowLabel = windowLabel;
        }

        @Override
        public void invoke(Map<String, Integer> userCounts, Context context) throws Exception {
            Map<String, Integer> topK = userCounts.entrySet().stream()
                    .sorted((e1, e2) -> e2.getValue().compareTo(e1.getValue()))
                    .limit(10)
                    .collect(HashMap::new, (m, e) -> m.put(e.getKey(), e.getValue()), HashMap::putAll);

            try (Jedis jedis = new Jedis("localhost", 6379)) {
                for (Map.Entry<String, Integer> entry : topK.entrySet()) {
                    String key = "topk:video-global:" + windowLabel;
                    jedis.zadd(key, entry.getValue(), entry.getKey());
                }
            }
        }
    }
}
