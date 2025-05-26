# Global Architecture in PyFlink
# ------------------------------
# - Kafka Topic: video_view_events (partitioned by videoId)
# - Multiple Flink jobs per videoId shard for: 1-hour, 1-day, 1-week windows
# - Each job aggregates Top-K per videoId and writes to Redis: topk:{videoId}:{window}
# - Global Aggregator Service reads Redis across videoIds and merges Top-K into: global_topk:{window}

from pyflink.datastream import StreamExecutionEnvironment, TimeCharacteristic
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream.connectors import FlinkKafkaConsumer
from pyflink.common.typeinfo import Types
from pyflink.datastream.window import SlidingEventTimeWindows
from pyflink.common.watermark_strategy import WatermarkStrategy
from datetime import datetime, timedelta
import redis
import json

KAFKA_BROKERS = 'localhost:9092'
TOPIC = 'video_view_events'
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
CHECKPOINT_PATH = 's3://my-flink-checkpoints/topk/'

# -----------------------------
# Redis Helper
# -----------------------------
def write_topk_to_redis(window_label, video_id, top_k_dict):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    key = f"topk:{video_id}:{window_label}"
    r.delete(key)
    for song_id, count in top_k_dict.items():
        r.zadd(key, {song_id: count})
    r.close()

# -----------------------------
# Aggregation Function
# -----------------------------
def extract_event(line):
    obj = json.loads(line)
    return (obj['videoId'], obj['songId'], obj['timestamp'])

def aggregate_topk(song_views):
    counts = {}
    for _, song_id, _ in song_views:
        counts[song_id] = counts.get(song_id, 0) + 1
    sorted_topk = dict(sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10])
    return sorted_topk

# -----------------------------
# Flink Job per Shard
# -----------------------------
def run_topk_job(window_size_minutes, slide_minutes, window_label):
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    env.enable_checkpointing(60000)
    env.get_checkpoint_config().set_checkpoint_storage(CHECKPOINT_PATH)

    kafka_props = {
        'bootstrap.servers': KAFKA_BROKERS,
        'group.id': f'flink-topk-{window_label}'
    }

    consumer = FlinkKafkaConsumer(
        TOPIC,
        SimpleStringSchema(),
        kafka_props
    )

    stream = env.add_source(consumer)

    stream = stream.map(lambda line: extract_event(line), output_type=Types.TUPLE([Types.STRING(), Types.STRING(), Types.LONG()]))

    stream = stream.assign_timestamps_and_watermarks(
        WatermarkStrategy.for_monotonous_timestamps().with_timestamp_assigner(lambda e, t: e[2])
    )

    stream.key_by(lambda x: x[0]) \  # videoId
          .window(SlidingEventTimeWindows.of(
              timedelta(minutes=window_size_minutes),
              timedelta(minutes=slide_minutes)
          ))           .process(lambda ctx, elements, out: out.collect((elements[0][0], aggregate_topk(elements))))           .add_sink(lambda result: write_topk_to_redis(window_label, result[0], result[1]))

    env.execute(f"Top-K Video Songs ({window_label})")

# -----------------------------
# Global Aggregator (Outside Flink)
# -----------------------------
def aggregate_global_topk(window_label):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    global_counts = {}
    for key in r.scan_iter(f"topk:*:{window_label}"):
        entries = r.zrevrange(key, 0, -1, withscores=True)
        for song_id, count in entries:
            song_id = song_id.decode()
            global_counts[song_id] = global_counts.get(song_id, 0) + count

    topk = dict(sorted(global_counts.items(), key=lambda x: x[1], reverse=True)[:10])
    r.delete(f"global_topk:{window_label}")
    for song_id, count in topk.items():
        r.zadd(f"global_topk:{window_label}", {song_id: count})
    r.close()

# -----------------------------
# Entrypoint for All Windows
# -----------------------------
if __name__ == '__main__':
    run_topk_job(60, 5, '1h')        # last hour, updated every 5 mins
    run_topk_job(1440, 60, '1d')     # last day, updated every hour
    run_topk_job(10080, 1440, '1w')  # last week, updated daily
