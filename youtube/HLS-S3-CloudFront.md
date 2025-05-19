# 🚀 Deploying HLS Video Streaming with S3 + CloudFront

This guide walks you through deploying an **HLS-based Adaptive Bitrate Streaming (ABR) system** using:

- Amazon **S3** to store `.m3u8` and `.ts` video segments
- Amazon **CloudFront** to serve content globally with caching and signed URL protection

---

## 📦 Folder Structure for HLS

Your S3 bucket should look like:

```
s3://my-hls-videos/
├── my-video/
│   ├── master.m3u8
│   ├── 360p/
│   │   ├── playlist.m3u8
│   │   ├── segment_000.ts
│   ├── 720p/
│   │   ├── playlist.m3u8
│   │   ├── segment_000.ts
```

---

## 🪜 Step-by-Step Deployment

### ✅ Step 1: Generate HLS Segments

```bash
ffmpeg -i input.mp4   -map 0:v -map 0:a -c:v libx264 -b:v:0 800k -s:v:0 640x360   -b:v:1 1600k -s:v:1 1280x720 -c:a aac -f hls   -var_stream_map "v:0,a:0 v:1,a:0"   -master_pl_name master.m3u8   -hls_segment_filename "%v/segment_%03d.ts"   "%v/playlist.m3u8"
```

### ✅ Step 2: Upload to S3

```bash
aws s3 sync ./output-folder s3://my-hls-videos/my-video/ --acl public-read
```

Or use **private access** and CloudFront signed URLs.

---

## ☁️ Step 3: Create CloudFront Distribution

- Origin: your S3 bucket
- Enable: "Restrict Bucket Access" (recommended)
- Enable: "Static file caching"
- Set Default Root Object: `master.m3u8`

Optional:
- Add a custom domain (e.g., `video.mysite.com`)
- Configure HTTPS with ACM

---

## 🔐 Step 4: (Optional) Signed URLs for Protected Streams

If using private buckets:

1. Create a CloudFront key pair
2. Generate signed URLs via SDK or Lambda@Edge
3. Add an expiry time to limit viewing duration

---

## 🌍 Final Playback URL

```
https://d123abc456.cloudfront.net/my-video/master.m3u8
```

Or with custom domain:

```
https://video.example.com/my-video/master.m3u8
```

---

## 🧪 Test Playback

Use [HLS.js](https://hls-js.netlify.app/demo/) or `<video>` with `MediaSource` API:

```html
<video controls autoplay width="720">
  <source src="https://video.example.com/my-video/master.m3u8" type="application/x-mpegURL">
</video>
```

---

## ✅ Benefits of Using CloudFront + S3

| Feature           | Benefit                         |
|------------------|----------------------------------|
| CDN edge caching | Fast delivery worldwide          |
| Private access    | Secure video distribution        |
| Signed URLs       | Controlled access per user       |
| Cost-efficient    | S3 + CloudFront is low-overhead  |

---

Let me know if you'd like to integrate with Lambda@Edge or DRM support like Widevine!
