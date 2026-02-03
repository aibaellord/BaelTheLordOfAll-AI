"""Phase 10-13 Module Exports"""

# Phase 10: Global Distributed Network
# Phase 13: Audio Processing
from core.audio.audio_processing import (AdvancedAudioSystem, AudioAnalysis,
                                         AudioAnalysisEngine, AudioCodec,
                                         AudioFormat, AudioQualityEnhancement,
                                         AudioSegment,
                                         MultiStreamAudioProcessor,
                                         SpeechLanguage,
                                         SpeechRecognitionEngine,
                                         SynthesisRequest, SynthesisResult,
                                         TextToSpeechEngine,
                                         TranscriptionResult)
from core.distributed.global_network import (ByzantineConsensusEngine,
                                             ConsensusAlgorithm,
                                             ConsensusProposal,
                                             DistributedNode,
                                             GlobalAgentNetwork, GlobalRouting,
                                             GlobalServiceMesh,
                                             GlobalTimeSeriesDB,
                                             MultiRegionDeployment, NodeRole,
                                             RaftReplicationEngine,
                                             ReplicationLog, ReplicationState)
# Phase 11: Computer Vision
from core.vision.computer_vision import (AdvancedComputerVisionSystem,
                                         BoundingBox, ClassificationResult,
                                         DetectionConfidence, DetectionResult,
                                         FaceDetection, FaceRecognitionEngine,
                                         ImageClassificationEngine,
                                         ObjectDetectionEngine,
                                         OpticalCharacterRecognition,
                                         PoseEstimate, PoseEstimationEngine,
                                         SegmentationResult, VisionModel)
# Phase 12: Real-time Video Analysis
from core.vision.video_analysis import (ActivitySegment,
                                        AdvancedVideoAnalysisSystem,
                                        FrameBuffer, FrameProcessingStatus,
                                        MotionDetectionEngine,
                                        MultiStreamOrchestrator,
                                        RealTimeAnalyticsEngine,
                                        SceneChangeDetection, StreamingMode,
                                        StreamingSession, TemporalFeature,
                                        TemporalSegmentation, VideoCodec,
                                        VideoFrame, VideoStreamProcessor)

__version__ = "10.0.0"
__all__ = [
    # Phase 10
    "ConsensusAlgorithm", "NodeRole", "ReplicationState", "DistributedNode",
    "ConsensusProposal", "ReplicationLog", "ByzantineConsensusEngine",
    "RaftReplicationEngine", "GlobalRouting", "GlobalServiceMesh",
    "MultiRegionDeployment", "GlobalTimeSeriesDB", "GlobalAgentNetwork",

    # Phase 11
    "VisionModel", "DetectionConfidence", "BoundingBox", "DetectionResult",
    "ClassificationResult", "SegmentationResult", "FaceDetection", "PoseEstimate",
    "ObjectDetectionEngine", "ImageClassificationEngine", "FaceRecognitionEngine",
    "PoseEstimationEngine", "OpticalCharacterRecognition", "AdvancedComputerVisionSystem",

    # Phase 12
    "StreamingMode", "VideoCodec", "FrameProcessingStatus", "VideoFrame",
    "TemporalFeature", "ActivitySegment", "StreamingSession", "FrameBuffer",
    "MotionDetectionEngine", "TemporalSegmentation", "SceneChangeDetection",
    "RealTimeAnalyticsEngine", "VideoStreamProcessor", "MultiStreamOrchestrator",
    "AdvancedVideoAnalysisSystem",

    # Phase 13
    "AudioFormat", "SpeechLanguage", "AudioCodec", "AudioSegment",
    "TranscriptionResult", "AudioAnalysis", "SynthesisRequest", "SynthesisResult",
    "SpeechRecognitionEngine", "TextToSpeechEngine", "AudioAnalysisEngine",
    "AudioQualityEnhancement", "MultiStreamAudioProcessor", "AdvancedAudioSystem"
]
