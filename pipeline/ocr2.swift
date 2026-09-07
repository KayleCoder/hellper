import Foundation
import Vision
import AppKit

for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
    let W = Double(cg.width), H = Double(cg.height)
    let req = VNRecognizeTextRequest()
    req.recognitionLanguages = ["ko-KR", "en-US"]
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = true
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    try? handler.perform([req])
    print("FILE\t\((path as NSString).lastPathComponent)\t\(Int(W))\t\(Int(H))")
    let obs = (req.results ?? []).sorted { $0.boundingBox.maxY > $1.boundingBox.maxY }
    for o in obs {
        guard let c = o.topCandidates(1).first else { continue }
        let b = o.boundingBox
        let x = b.minX * W, y = (1.0 - b.maxY) * H
        let w = b.width * W, h = b.height * H
        print("L\t\(Int(x))\t\(Int(y))\t\(Int(w))\t\(Int(h))\t\(String(format:"%.2f",c.confidence))\t\(c.string)")
    }
}
