import Foundation
import ScreenCaptureKit
import CoreMedia
import AVFoundation
import Darwin

@available(macOS 13.0, *)
class AudioStreamer: NSObject, SCStreamOutput, SCStreamDelegate {
    func stream(_ stream: SCStream, didOutputSampleBuffer sampleBuffer: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .audio else { return }
        
        var audioBufferList = AudioBufferList()
        var blockBuffer: CMBlockBuffer?
        
        let status = CMSampleBufferGetAudioBufferListWithRetainedBlockBuffer(
            sampleBuffer,
            bufferListSizeNeededOut: nil,
            bufferListOut: &audioBufferList,
            bufferListSize: MemoryLayout<AudioBufferList>.size,
            blockBufferAllocator: nil,
            blockBufferMemoryAllocator: nil,
            flags: 0,
            blockBufferOut: &blockBuffer
        )
        
        if status == noErr {
            withUnsafePointer(to: &audioBufferList.mBuffers) { buffersPtr in
                if let mData = buffersPtr.pointee.mData {
                    let size = Int(buffersPtr.pointee.mDataByteSize)
                    if size > 0 {
                        _ = Darwin.write(STDOUT_FILENO, mData, size)
                    }
                }
            }
        }
    }
    
    func stream(_ stream: SCStream, didStopWithError error: Error) {
        fputs("SCStream stopped with error: \(error)\n", stderr)
        exit(1)
    }
}

Task {
    if #available(macOS 13.0, *) {
        do {
            let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
            guard let display = content.displays.first else {
                fputs("No display found\n", stderr)
                exit(1)
            }
            
            let filter = SCContentFilter(display: display, excludingApplications: [], exceptingWindows: [])
            let config = SCStreamConfiguration()
            config.capturesAudio = true
            config.sampleRate = 44100
            config.channelCount = 1
            config.excludesCurrentProcessAudio = false
            config.width = 16
            config.height = 16
            config.minimumFrameInterval = CMTime(value: 1, timescale: 1)
            
            let streamer = AudioStreamer()
            let stream = SCStream(filter: filter, configuration: config, delegate: streamer)
            let queue = DispatchQueue(label: "audio-stream-queue", qos: .userInteractive)
            try stream.addStreamOutput(streamer, type: .audio, sampleHandlerQueue: queue)
            
            try await stream.startCapture()
            fputs("SCK_STREAM_READY\n", stderr)
            fflush(stderr)
        } catch {
            fputs("SCK_STREAM_ERROR: \(error)\n", stderr)
            exit(1)
        }
    } else {
        fputs("SCK_STREAM_ERROR: macOS 13.0+ required\n", stderr)
        exit(1)
    }
}

RunLoop.main.run()
