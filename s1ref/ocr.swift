import Foundation
import Vision
import AppKit

// usage: ocr <scale> <img1> [img2 ...]   -> prints "===FILE:<path>" then lines
let args = CommandLine.arguments
guard args.count > 2, let scale = Double(args[1]) else { exit(2) }

func loadCG(_ path: String, scale: Double) -> CGImage? {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return nil }
    if scale == 1.0 { return cg }
    let w = Int(Double(cg.width) * scale), h = Int(Double(cg.height) * scale)
    guard w > 0, h > 0, h < 30000,
          let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                              space: CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return cg }
    ctx.interpolationQuality = .high
    ctx.draw(cg, in: CGRect(x: 0, y: 0, width: w, height: h))
    return ctx.makeImage() ?? cg
}

for path in args.dropFirst(2) {
    print("===FILE:\(path)")
    guard let cg = loadCG(path, scale: scale) else { print("[[load-failed]]"); continue }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["zh-Hant", "zh-Hans", "en-US"]
    req.usesLanguageCorrection = true
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    do { try handler.perform([req]) } catch { print("[[ocr-failed]]"); continue }
    guard let obs = req.results else { continue }
    // sort top-to-bottom (Vision origin is bottom-left), then left-to-right
    let sorted = obs.sorted { a, b in
        let ay = 1 - a.boundingBox.midY, by = 1 - b.boundingBox.midY
        if abs(ay - by) > 0.012 { return ay < by }
        return a.boundingBox.midX < b.boundingBox.midX
    }
    for o in sorted {
        if let c = o.topCandidates(1).first, c.confidence > 0.3 {
            print(c.string)
        }
    }
}
