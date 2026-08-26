import Foundation
import Vision
import CoreImage
import AppKit

let args = CommandLine.arguments
guard args.count >= 3 else { print("usage: facecrop in out [size]"); exit(1) }
let inURL = URL(fileURLWithPath: args[1]), outURL = URL(fileURLWithPath: args[2])
let outSize = args.count > 3 ? Int(args[3])! : 640

guard let src = CGImageSourceCreateWithURL(inURL as CFURL, nil),
      let cg = CGImageSourceCreateImageAtIndex(src, 0, nil) else { print("ERR load"); exit(1) }
let W = CGFloat(cg.width), H = CGFloat(cg.height)

// find faces
var faces: [CGRect] = []
let req = VNDetectFaceRectanglesRequest()
try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
for obs in (req.results ?? []) {
    let b = obs.boundingBox                       // normalised, origin bottom-left
    faces.append(CGRect(x: b.minX * W, y: (1 - b.minY - b.height) * H, width: b.width * W, height: b.height * H))
}
// keep the biggest face (group shots: the subject is usually the largest)
faces.sort { $0.width * $0.height > $1.width * $1.height }

var cx = W / 2, cy = H * 0.38, size = min(W, H)   // fallback: upper-middle, typical for portraits
var how = "no-face-fallback"
if let f = faces.first {
    cx = f.midX; cy = f.midY
    size = min(min(W, H), max(f.width, f.height) * 3.2)
    cy += size * 0.10                              // a little headroom above, shoulders below
    how = "face(\(faces.count)) \(Int(f.width))x\(Int(f.height))px"
}
var x = cx - size / 2, y = cy - size / 2
x = max(0, min(x, W - size)); y = max(0, min(y, H - size))

guard let cropped = cg.cropping(to: CGRect(x: x, y: y, width: size, height: size)) else { print("ERR crop"); exit(1) }
let ctx = CGContext(data: nil, width: outSize, height: outSize, bitsPerComponent: 8, bytesPerRow: 0,
                    space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
ctx.interpolationQuality = .high
ctx.draw(cropped, in: CGRect(x: 0, y: 0, width: outSize, height: outSize))
guard let out = ctx.makeImage(),
      let dest = CGImageDestinationCreateWithURL(outURL as CFURL, "public.jpeg" as CFString, 1, nil) else { print("ERR write"); exit(1) }
CGImageDestinationAddImage(dest, out, [kCGImageDestinationLossyCompressionQuality: 0.82] as CFDictionary)
CGImageDestinationFinalize(dest)
print("\(inURL.lastPathComponent): \(how) -> crop \(Int(size))px at (\(Int(x)),\(Int(y)))")
