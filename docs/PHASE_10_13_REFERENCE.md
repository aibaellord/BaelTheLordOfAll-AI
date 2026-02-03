# Phase 10-13 Quick Reference Guide

**Complete code examples and operations for Phases 10-13.**

---

## Phase 10: Global Distributed Network

### Quick Start: Initialize Global Network

```python
import asyncio
from core.distributed.global_network import GlobalAgentNetwork

async def main():
    network = GlobalAgentNetwork()

    # Initialize across 9 regions
    regions = [
        "us-east", "us-west", "eu-west", "eu-central",
        "ap-southeast", "ap-northeast", "ap-south", "sa-east", "af-south"
    ]

    await network.initialize_network(regions)
    print("Global network initialized")

    # Execute distributed task
    task = {
        "name": "process_request",
        "priority": "high"
    }

    result = await network.execute_distributed_task(task)
    print(f"Task result: {result}")

asyncio.run(main())
```

### Byzantine Consensus Operations

```python
from core.distributed.global_network import (
    ByzantineConsensusEngine,
    DistributedNode,
    NodeRole,
    ConsensusProposal
)
from datetime import datetime

# Initialize consensus engine (tolerates 1 faulty node)
consensus = ByzantineConsensusEngine(max_faulty_nodes=1)

# Register nodes
for i in range(4):  # 4 nodes = 3f+1 where f=1
    node = DistributedNode(
        id=f"node_{i}",
        region=f"region_{i}",
        node_role=NodeRole.PRIMARY if i == 0 else NodeRole.REPLICA
    )
    consensus.register_node(node)

# Create and reach consensus
async def consensus_example():
    proposal = ConsensusProposal(
        proposal_id="prop_001",
        operation="update_state",
        data={"key": "value"},
        timestamp=datetime.now(),
        proposer_id="node_0",
        quorum_size=3  # Majority
    )

    success = await consensus.reach_consensus(proposal)
    print(f"Consensus reached: {success}")

    stats = consensus.get_consensus_stats()
    print(f"Stats: {stats}")
```

### Raft Replication

```python
from core.distributed.global_network import RaftReplicationEngine, ReplicationLog

replication = RaftReplicationEngine()

# Register nodes
for i in range(3):
    from core.distributed.global_network import DistributedNode, NodeRole
    node = DistributedNode(
        id=f"replica_{i}",
        region="us-east",
        node_role=NodeRole.PRIMARY if i == 0 else NodeRole.REPLICA
    )
    replication.register_node(node)

async def replication_example():
    # Create replication entries
    entries = [
        ReplicationLog(
            index=i,
            term=1,
            operation="write",
            data={"key": f"key_{i}", "value": f"value_{i}"},
            timestamp=datetime.now()
        )
        for i in range(10)
    ]

    # Append entries (auto-replicates)
    success = await replication.append_entries(entries)
    print(f"Entries replicated: {success}")

    # Get stats
    stats = replication.get_replication_stats()
    print(f"Replication stats: {stats}")

    # Handle leader failure
    await replication.handle_leader_failure("replica_0")
    print("Leader election completed")
```

### Global Routing

```python
from core.distributed.global_network import GlobalRouting

routing = GlobalRouting()

async def routing_example():
    # Route request to optimal region
    best_region = await routing.route_request(
        request_id="req_001",
        user_region="us-west",
        required_latency=100  # max 100ms
    )

    print(f"Routed to: {best_region}")

    # Adapt to network changes
    await routing.adapt_to_network()

    # Get routing stats
    stats = routing.get_routing_stats()
    print(f"Routing stats: {stats}")
```

---

## Phase 11: Computer Vision

### Quick Start: Analyze Image

```python
import asyncio
from core.vision.computer_vision import AdvancedComputerVisionSystem, VisionModel

async def main():
    vision = AdvancedComputerVisionSystem()

    # Load image
    with open("image.jpg", "rb") as f:
        image_data = f.read()

    # Comprehensive analysis
    result = await vision.analyze_image(
        image_id="img_001",
        image_data=image_data
    )

    print(f"Analysis result: {result}")

asyncio.run(main())
```

### Object Detection

```python
from core.vision.computer_vision import ObjectDetectionEngine, VisionModel

detection = ObjectDetectionEngine()

async def detection_example():
    # Detect with YOLO (fastest, 30 fps)
    result = await detection.detect_objects(
        image_id="img_001",
        image_data=image_data,
        model=VisionModel.YOLO_V8,
        confidence_threshold=0.5
    )

    # Print detections
    for detection in result.detections:
        print(f"{detection.class_name}: {detection.confidence:.2%}")

    # Get statistics
    stats = detection.get_detection_stats()
    print(f"Detection stats: {stats}")
```

### Image Classification

```python
from core.vision.computer_vision import ImageClassificationEngine, VisionModel

classification = ImageClassificationEngine()

async def classification_example():
    # Classify with ResNet-50 (1000 fps)
    result = await classification.classify_image(
        image_id="img_001",
        image_data=image_data,
        model=VisionModel.RESNET_50,
        top_k=5
    )

    # Print top classes
    for class_name, confidence in result.top_classes:
        print(f"{class_name}: {confidence:.2%}")

    # Batch classification
    images = {
        "img_001": image_data_1,
        "img_002": image_data_2,
    }

    batch_results = await classification.batch_classify(images)
```

### Face Recognition

```python
from core.vision.computer_vision import FaceRecognitionEngine

faces = FaceRecognitionEngine()

async def face_example():
    # Detect faces with attributes
    detected_faces = await faces.detect_faces(
        image_id="img_001",
        image_data=image_data,
        detect_attributes=True
    )

    # Recognize each face
    known_faces_db = {
        "person_1": [0.1, 0.2, ...],  # 512D embedding
        "person_2": [0.3, 0.4, ...],
    }

    for face in detected_faces:
        identity = await faces.recognize_face(
            face.embedding,
            known_faces_db
        )

        if identity:
            print(f"Person: {identity[0]}, confidence: {identity[1]:.2%}")
            print(f"Age: {face.age}, Gender: {face.gender}, Emotion: {face.emotion}")
```

### Pose Estimation

```python
from core.vision.computer_vision import PoseEstimationEngine, VisionModel

poses = PoseEstimationEngine()

async def pose_example():
    # Estimate pose
    pose_estimates = await poses.estimate_pose(
        image_id="img_001",
        image_data=image_data,
        model=VisionModel.OPENPOSE
    )

    for pose in pose_estimates:
        # Get keypoints
        for joint_name, (x, y, confidence) in pose.keypoints.items():
            print(f"{joint_name}: ({x:.1f}, {y:.1f}) - {confidence:.2%}")

        # Draw skeleton
        for (joint1, joint2) in pose.skeleton_edges:
            p1 = pose.keypoints[joint1]
            p2 = pose.keypoints[joint2]
            # Draw line from p1 to p2
```

### OCR

```python
from core.vision.computer_vision import OpticalCharacterRecognition

ocr = OpticalCharacterRecognition()

async def ocr_example():
    # Extract text (50+ languages)
    result = await ocr.extract_text(
        image_id="img_001",
        image_data=image_data,
        languages=["english", "spanish"]
    )

    print(f"Extracted text: {result['text']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Word count: {result['word_count']}")

    # Extract handwriting
    handwriting = await ocr.extract_handwriting(
        image_id="img_002",
        image_data=image_data
    )
```

---

## Phase 12: Real-time Video Analysis

### Quick Start: Analyze Video Stream

```python
import asyncio
from core.vision.video_analysis import AdvancedVideoAnalysisSystem

async def main():
    video = AdvancedVideoAnalysisSystem()

    # Analyze video stream
    result = await video.analyze_video_stream(
        video_source="rtmp://example.com/live",
        stream_id="stream_001",
        duration_seconds=60
    )

    stats = video.get_system_stats()
    print(f"Processing stats: {stats}")

asyncio.run(main())
```

### Video Stream Processing

```python
from core.vision.video_analysis import (
    VideoStreamProcessor,
    StreamingMode,
    VideoCodec,
    VideoFrame
)
from datetime import datetime

processor = VideoStreamProcessor()

async def streaming_example():
    # Start stream
    session = await processor.start_stream(
        session_id="stream_001",
        source_url="rtmp://example.com/live",
        mode=StreamingMode.ANALYSIS,
        codec=VideoCodec.H265,
        fps=30,
        resolution=(1920, 1080)
    )

    # Process frames
    frame_counter = 0
    async for frame_bytes in stream_source:
        frame = VideoFrame(
            frame_id=frame_counter,
            timestamp=datetime.now(),
            frame_data=frame_bytes,
            width=1920,
            height=1080,
            fps=30
        )

        # Process frame
        analysis = await processor.process_frame("stream_001", frame)

        if analysis.get("motion", {}).get("detected"):
            print(f"Motion detected: {analysis['motion']['magnitude']:.2%}")

        if analysis.get("scene_change"):
            print("Scene change detected")

        frame_counter += 1

    # Stop stream
    stats = await processor.stop_stream("stream_001")
    print(f"Stream stats: {stats}")
```

### Motion Detection

```python
from core.vision.video_analysis import MotionDetectionEngine

motion = MotionDetectionEngine()

async def motion_example():
    # Detect motion between frames
    detected, magnitude = await motion.detect_motion(frame1, frame2)
    print(f"Motion: {detected}, Magnitude: {magnitude:.2%}")

    # Get motion trajectory
    features = await motion.get_motion_trajectory(frames)

    for feature in features:
        print(f"Motion at frames {feature.frames_involved}: {feature.value:.2%}")
```

### Temporal Segmentation

```python
from core.vision.video_analysis import TemporalSegmentation

segmentation = TemporalSegmentation()

async def segmentation_example():
    # Segment video into activity regions
    segments = await segmentation.segment_video(
        motion_values=[0.05, 0.08, 0.45, 0.50, 0.12],
        frame_ids=[0, 1, 2, 3, 4],
        fps=30
    )

    for segment in segments:
        print(f"{segment.activity_type}: {segment.start_frame}-{segment.end_frame}")
        print(f"  Duration: {segment.duration_ms:.0f}ms, Intensity: {segment.intensity:.2%}")
```

### Multi-Stream Orchestration

```python
from core.vision.video_analysis import MultiStreamOrchestrator

orchestrator = MultiStreamOrchestrator(max_streams=50)

async def multi_stream_example():
    # Add multiple streams
    for i in range(50):
        await orchestrator.add_stream(
            processor_id=f"processor_{i // 10}",
            session_id=f"stream_{i:03d}",
            source_url=f"rtmp://source{i}.com/live",
            fps=30
        )

    print("50 streams started")

    # Process all streams
    results = await orchestrator.process_all_streams()

    # Get orchestration stats
    stats = orchestrator.get_orchestration_stats()
    print(f"Processing capacity: {stats['processing_capacity']}")
```

---

## Phase 13: Audio Processing

### Quick Start: Process Audio

```python
import asyncio
from core.audio.audio_processing import AdvancedAudioSystem, SpeechLanguage

async def main():
    audio = AdvancedAudioSystem()

    # Load audio
    with open("audio.wav", "rb") as f:
        audio_data = f.read()

    # Process audio
    result = await audio.process_audio_file(
        audio_id="audio_001",
        audio_data=audio_data,
        language=SpeechLanguage.ENGLISH
    )

    print(f"Transcription: {result['transcription']['text']}")
    print(f"Confidence: {result['transcription']['confidence']:.2%}")

asyncio.run(main())
```

### Speech Recognition

```python
from core.audio.audio_processing import SpeechRecognitionEngine, SpeechLanguage

stt = SpeechRecognitionEngine()

async def transcription_example():
    # Transcribe audio
    result = await stt.transcribe_audio(
        audio_id="audio_001",
        audio_data=audio_data,
        language=SpeechLanguage.ENGLISH
    )

    print(f"Text: {result.text}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Word count: {result.word_count}")

    # Get alternative transcriptions
    for text, confidence in result.alternative_texts:
        print(f"  Alternative: {text} ({confidence:.2%})")

    # Continuous transcription (for streaming)
    chunks = await stt.continuous_transcription(
        audio_stream=long_audio_bytes,
        language=SpeechLanguage.ENGLISH
    )

    for i, chunk_result in enumerate(chunks):
        print(f"Chunk {i}: {chunk_result.text}")
```

### Text-to-Speech

```python
from core.audio.audio_processing import TextToSpeechEngine, SpeechLanguage, AudioFormat

tts = TextToSpeechEngine()

async def synthesis_example():
    # Synthesize text
    result = await tts.synthesize_text(
        request_id="tts_001",
        text="Hello world, this is a test",
        language=SpeechLanguage.ENGLISH,
        speaker_id="speaker_5",
        audio_format=AudioFormat.OPUS
    )

    print(f"Audio generated: {result.duration_ms:.0f}ms")
    print(f"Sample rate: {result.sample_rate}Hz")
    print(f"Quality: {result.confidence:.2%}")

    # Synthesize with emotion
    emotional = await tts.synthesize_with_emotion(
        request_id="tts_002",
        text="I'm so happy!",
        emotion="happy",
        language=SpeechLanguage.ENGLISH
    )

    print(f"Emotional synthesis: {emotional.duration_ms:.0f}ms")
```

### Audio Analysis

```python
from core.audio.audio_processing import AudioAnalysisEngine

analysis = AudioAnalysisEngine()

async def analysis_example():
    # Analyze audio
    result = await analysis.analyze_audio(
        audio_id="audio_001",
        audio_data=audio_data,
        sample_rate=16000
    )

    print(f"Volume: {result.volume_db} dB")
    print(f"Loudness: {result.loudness_lufs} LUFS")
    print(f"Pitch: {result.pitch_hz} Hz")
    print(f"Emotion: {result.emotion}")
    print(f"Voice active: {result.voice_activity}")

    # Detect emotion
    emotion, confidence = await analysis.detect_emotion(audio_data)
    print(f"Detected emotion: {emotion} ({confidence:.2%})")

    # Voice activity detection
    segments = await analysis.voice_activity_detection(audio_data)
    print(f"Speech segments: {segments}")
```

### Audio Quality Enhancement

```python
from core.audio.audio_processing import AudioQualityEnhancement

enhancement = AudioQualityEnhancement()

async def enhancement_example():
    # Denoise
    denoised = await enhancement.denoise(
        audio_data=audio_data,
        noise_reduction_strength=0.8
    )
    print("Audio denoised")

    # Normalize to streaming standard (-14 LUFS)
    normalized = await enhancement.normalize_audio(
        audio_data=denoised,
        target_loudness_lufs=-14
    )
    print("Audio normalized to -14 LUFS")

    # Remove silence
    trimmed = await enhancement.remove_silence(normalized)
    print("Silence removed")

    # Enhance speech clarity
    enhanced = await enhancement.enhance_speech(
        audio_data=trimmed,
        enhancement_type="clarity"
    )
    print("Speech enhanced")

    return enhanced
```

### Multi-Stream Audio

```python
from core.audio.audio_processing import MultiStreamAudioProcessor, SpeechLanguage

processor = MultiStreamAudioProcessor(max_streams=50)

async def multi_stream_audio():
    # Start 50 audio streams
    for i in range(50):
        await processor.start_stream(
            stream_id=f"audio_stream_{i:03d}",
            audio_source=f"mic://{i}",
            language=SpeechLanguage.ENGLISH
        )

    print("50 audio streams started")

    # Process frames from each stream
    # (In production: would be continuous from audio source)
    for stream_id in [f"audio_stream_{i:03d}" for i in range(50)]:
        result = await processor.process_audio_frame(
            stream_id=stream_id,
            frame_data=audio_frame_data
        )

    # Stop and get stats
    stats = await processor.stop_stream("audio_stream_000")
    print(f"Stream stats: {stats}")
```

---

## Complete Integration Example

```python
import asyncio
from core.distributed.global_network import GlobalAgentNetwork
from core.vision.computer_vision import AdvancedComputerVisionSystem
from core.vision.video_analysis import AdvancedVideoAnalysisSystem
from core.audio.audio_processing import AdvancedAudioSystem

async def integrated_multimodal():
    # Initialize all systems
    network = GlobalAgentNetwork()
    vision = AdvancedComputerVisionSystem()
    video = AdvancedVideoAnalysisSystem()
    audio = AdvancedAudioSystem()

    # Initialize global network
    regions = ["us-east", "eu-west", "ap-southeast"]
    await network.initialize_network(regions)

    # Process video and audio together
    video_frame = b"video_frame_data"
    audio_sample = b"audio_sample_data"

    # Vision analysis
    vision_result = await vision.analyze_image(
        image_id="frame_001",
        image_data=video_frame
    )

    # Audio analysis
    audio_result = await audio.process_audio_file(
        audio_id="audio_001",
        audio_data=audio_sample
    )

    # Combine results
    multimodal_result = {
        "frame": vision_result,
        "audio": audio_result,
        "timestamp": "2024-01-01T00:00:00"
    }

    # Distribute globally
    task = {
        "name": "multimodal_analysis",
        "data": multimodal_result
    }

    distributed = await network.execute_distributed_task(task)

    # Get all stats
    stats = {
        "network": network.get_network_stats(),
        "vision": vision.get_vision_stats(),
        "video": video.get_system_stats(),
        "audio": audio.get_system_stats()
    }

    return stats

asyncio.run(integrated_multimodal())
```

---

## Common Operations

### Get System Statistics

```python
# Phase 10: Global Distribution
network_stats = network.get_network_stats()

# Phase 11: Computer Vision
vision_stats = vision.get_vision_stats()

# Phase 12: Video Analysis
video_stats = video.get_system_stats()

# Phase 13: Audio Processing
audio_stats = audio.get_system_stats()

# Print all stats
print(network_stats)
print(vision_stats)
print(video_stats)
print(audio_stats)
```

### Handle Errors

```python
import asyncio
try:
    result = await vision.analyze_image(image_id, image_data)
except Exception as e:
    print(f"Error: {e}")

# Async error handling
async def safe_operation():
    try:
        await network.execute_distributed_task(task)
    except Exception as e:
        logger.error(f"Task failed: {e}")
        # Implement fallback
```

### Batch Operations

```python
# Batch vision analysis
images = {
    "img_1": image_data_1,
    "img_2": image_data_2,
    "img_3": image_data_3
}

results = await vision.classification.batch_classify(images)

# Batch audio processing
audio_files = [audio_1, audio_2, audio_3]

for audio_data in audio_files:
    result = await audio.process_audio_file(
        audio_id=f"audio_{i}",
        audio_data=audio_data
    )
```

---

## Performance Optimization

### Parallel Processing

```python
import asyncio

async def parallel_processing():
    # Process vision and audio in parallel
    vision_task = vision.analyze_image("img_001", image_data)
    audio_task = audio.process_audio_file("audio_001", audio_data)

    # Wait for both
    vision_result, audio_result = await asyncio.gather(
        vision_task,
        audio_task
    )

    return vision_result, audio_result
```

### Stream Configuration

```python
# Low latency (real-time)
await processor.start_stream(
    session_id="stream_001",
    source_url="rtmp://example.com",
    codec=VideoCodec.H265,  # Lower bitrate
    fps=30
)

# High quality (recording)
await processor.start_stream(
    session_id="stream_002",
    source_url="rtmp://example.com",
    codec=VideoCodec.H264,  # Better compatibility
    fps=60
)
```

---

## Troubleshooting

| Issue              | Solution                                  |
| ------------------ | ----------------------------------------- |
| Vision models slow | Use YOLO (30 fps) instead of Faster R-CNN |
| Video drops        | Reduce FPS or codec (H265 < H264)         |
| Audio lag          | Enable streaming mode (low latency)       |
| Memory high        | Reduce frame buffer size or stream count  |
| Network partition  | Automatic failover via circuit breakers   |

---

## Additional Resources

- **Full Documentation:** `docs/PHASE_10_13_COMPLETE.md`
- **Integration Demo:** `examples/phase_10_13_demo.py`
- **Project Status:** `PROJECT_STATUS_PHASE_10_13.md`
- **Source Code:** `core/distributed/`, `core/vision/`, `core/audio/`

---

**Last Updated:** Phase 10-13 Complete
**Version:** 10.0.0
**Status:** Production Ready
