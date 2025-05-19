# 🎞️ Adaptive Bitrate Streaming with HLS and MPEG-DASH

This guide explains how **Adaptive Bitrate Streaming (ABR)** works using **HLS** and **MPEG-DASH**, with examples, streaming segment storage, and FFMPEG commands for generating HLS content.

---

## 📦 What is Adaptive Bitrate (ABR) Streaming?

ABR allows a video player to:

- Stream video in **multiple qualities** (e.g., 240p, 480p, 1080p)
- Switch between qualities **dynamically**, based on:
  - User’s network speed
  - Buffer conditions
  - Device capability

---

## 📺 How It Works

1. The video is **encoded into multiple resolutions/bitrates**.
2. Each rendition is **split into segments** (2–10 seconds).
3. A **manifest/playlist** file (M3U8 or MPD) tells the player what to download.
4. The player **adapts in real-time** to changing conditions.

---

## 🍏 HLS (HTTP Live Streaming)

### Files:
- `.m3u8`: Playlist files (master + variant)
- `.ts` or `.fmp4`: Segment files

### Master Playlist Example:

```m3u8
#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360
360p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1600000,RESOLUTION=1280x720
720p.m3u8
```

### Variant Playlist:

```m3u8
#EXTM3U
#EXTINF:6.006,
segment1.ts
#EXTINF:5.994,
segment2.ts
```

---

## 📦 S3 Storage Structure for Segments

```
s3://my-video-bucket/
├── my-video/
│   ├── master.m3u8
│   ├── 360p/
│   │   ├── 360p.m3u8
│   │   ├── segment1.ts
│   │   ├── segment2.ts
│   ├── 720p/
│   │   ├── 720p.m3u8
│   │   ├── segment1.ts
```

- You can enable **CloudFront** to serve segments via CDN.
- All segments are publicly readable or protected via signed URLs.

---

## 🧪 FFMPEG Commands: Generate HLS from MP4

### Basic HLS with 720p

```bash
ffmpeg -i input.mp4   -profile:v baseline -level 3.0 -s 1280x720 -start_number 0   -hls_time 10 -hls_list_size 0 -f hls 720p.m3u8
```

### Multi-bitrate HLS with Master Playlist

```bash
ffmpeg -i input.mp4   -map 0:v -map 0:a -c:v libx264 -b:v:0 800k -s:v:0 640x360   -b:v:1 1600k -s:v:1 1280x720 -c:a aac -f hls   -var_stream_map "v:0,a:0 v:1,a:0"   -master_pl_name master.m3u8   -hls_segment_filename "%v/segment_%03d.ts"   "%v/playlist.m3u8"
```

---

## 🧠 HLS vs MPEG-DASH

| Feature              | HLS                        | MPEG-DASH                   |
|---------------------|----------------------------|-----------------------------|
| Playlist format      | M3U8                       | MPD (XML)                   |
| Segment format       | `.ts`, `.fmp4`             | `.mp4`, `.m4s`              |
| CDN support          | Excellent (CloudFront, etc)| Excellent                   |
| Device support       | Native on iOS, Safari      | Better on Android, browsers |

---

## ✅ Summary

- ABR enables smooth streaming with multiple quality levels.
- HLS uses `.m3u8` + `.ts`, DASH uses `.mpd` + `.mp4`
- S3 can store segments in structured folders by quality
- FFMPEG can generate adaptive streams with master playlists

---

Let me know if you want to include DRM, subtitles, or DASH generation examples!
