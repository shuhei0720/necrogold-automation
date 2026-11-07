import Foundation
import CoreGraphics
import ImageIO

func require(_ value: Bool, _ label: String) {
    if !value { print("FAIL \(label)"); exit(1) }
}
func image(_ pixels: [UInt8], _ width: Int, _ height: Int, bytesPerRow: Int? = nil) -> CGImage {
    let space = CGColorSpace(name: CGColorSpace.sRGB)!
    let provider = CGDataProvider(data: Data(pixels) as CFData)!
    return CGImage(width: width, height: height, bitsPerComponent: 8, bitsPerPixel: 32,
        bytesPerRow: bytesPerRow ?? width * 4, space: space,
        bitmapInfo: CGBitmapInfo(rawValue: CGBitmapInfo.byteOrder32Big.rawValue |
            CGImageAlphaInfo.premultipliedLast.rawValue), provider: provider,
        decode: nil, shouldInterpolate: false, intent: .defaultIntent)!
}
let pixels = (1...6).flatMap { [UInt8($0*20), UInt8(0), UInt8(0), UInt8(255)] }
let original = image(pixels, 3, 2)
let expected: [[UInt8]] = [[1,2,3,4,5,6],[3,2,1,6,5,4],[6,5,4,3,2,1],[4,5,6,1,2,3],
    [1,4,2,5,3,6],[4,1,5,2,6,3],[6,3,5,2,4,1],[3,6,2,5,1,4]]
for orientation in 1...8 {
    let w = orientation >= 5 ? 2 : 3
    let h = orientation >= 5 ? 3 : 2
    guard let rgba = NG2Raster.normalize(original, orientation: orientation, outputWidth: w, outputHeight: h) else {
        require(false, "orientation_\(orientation)_created"); fatalError()
    }
    let red = stride(from: 0, to: rgba.count, by: 4).map { rgba[$0] / 20 }
    require(red == expected[orientation-1], "orientation_\(orientation)_asymmetric_pixels")
    require(stride(from: 3, to: rgba.count, by: 4).allSatisfy { rgba[$0] == 255 }, "opaque_\(orientation)")
}
require(NG2Raster.normalize(original, orientation: 0, outputWidth: 3, outputHeight: 2) == nil, "orientation_invalid")
require(NG2Raster.normalize(original, outputWidth: 2, outputHeight: 2) == nil, "aspect_invalid")
require(NG2Raster.normalize(original, outputWidth: 0, outputHeight: 0) == nil, "size_invalid")
let pixel: [UInt8] = [10, 20, 30, 255]
let full: [UInt8] = Array(repeating: pixel, count: 896*414).flatMap { $0 }
// The array-of-arrays initializer above deliberately uses the standard
// collection API so no native word endian assumptions enter the fixture.
let fullImage = image(full, 896, 414)
let normalized = NG2Raster.normalize(fullImage)!
require(normalized.count == 896*414*4, "rgba_length")
require(normalized.prefix(4) == Data([10,20,30,255]), "rgba_byte_order")
// Padding belongs to the source CGImage, not to the normalized pixel ABI.
var padded: [UInt8] = []
for row in 0..<2 {
    padded.append(contentsOf: pixels[(row*12)..<(row*12+12)])
    padded.append(contentsOf: [222, 111, 99, 88, 77, 66, 55, 44])
}
let paddedImage = image(padded, 3, 2, bytesPerRow: 20)
require(NG2Raster.normalize(paddedImage, outputWidth: 3, outputHeight: 2) == Data(pixels),
    "source_padded_stride_not_pixels")
let alpha: [UInt8] = [0, 0, 0, 0, 64, 32, 16, 128]
let composited = NG2Raster.normalize(image(alpha, 2, 1), outputWidth: 2, outputHeight: 1)!
require(composited.prefix(4) == Data([0, 0, 0, 255]), "transparent_composites_opaque_black")
require(abs(Int(composited[4])-64) <= 1 && abs(Int(composited[5])-32) <= 1 &&
    abs(Int(composited[6])-16) <= 1 && composited[7] == 255, "semialpha_composites_opaque_black")
for scale in [2, 3] {
    let scaledPixels: [UInt8] = Array(repeating: pixel, count: 896*414*scale*scale).flatMap { $0 }
    let scaled = NG2Raster.normalize(image(scaledPixels, 896*scale, 414*scale))!
    require(scaled.count == normalized.count, "production_scale_\(scale)_normalized_length")
    var pixelsMatch = true
    for offset in stride(from: 0, to: scaled.count, by: 4) {
        let red = Int(scaled[offset])
        let green = Int(scaled[offset+1])
        let blue = Int(scaled[offset+2])
        if abs(red-10) > 1 { pixelsMatch = false }
        if abs(green-20) > 1 { pixelsMatch = false }
        if abs(blue-30) > 1 { pixelsMatch = false }
        if scaled[offset+3] != 255 { pixelsMatch = false }
    }
    require(pixelsMatch, "production_scale_\(scale)_sRGB_RGBA")
}
let wrongGeometry: [UInt8] = Array(repeating: pixel, count: 895*414).flatMap { $0 }
require(NG2Raster.normalize(image(wrongGeometry, 895, 414)) == nil, "unknown_production_geometry_rejected")
let overLimit: [UInt8] = Array(repeating: pixel, count: 4097).flatMap { $0 }
require(NG2Raster.normalize(image(overLimit, 4097, 1), outputWidth: 4097, outputHeight: 1) == nil,
    "oversize_source_rejected")
require(NG2Raster.decode(Data([1, 2, 3])) == nil, "invalid_encoded_image_rejected")
require(NG2Raster.png(Data(count: 16)) == nil, "invalid_export_raster_rejected")
var scene = NG2Scene()
let result = normalized.withUnsafeBytes {
    ng2_analyze_rgba($0.bindMemory(to: UInt8.self).baseAddress, normalized.count, 3584, &scene)
}
require(result == 0 && scene.abi_version == 1 && scene.struct_size == UInt32(MemoryLayout<NG2Scene>.size),
    "production_raster_real_C_ABI")
require(scene.state == 0, "unknown_pixels_cannot_authorize_floor")
let invalid = normalized.withUnsafeBytes {
    ng2_analyze_rgba($0.bindMemory(to: UInt8.self).baseAddress, normalized.count-1, 3584, &scene)
}
require(invalid < 0 && scene.state == 0, "real_C_short_buffer_refused")
let encoded = NG2Raster.png(normalized)!
require(encoded.starts(with: [137,80,78,71,13,10,26,10]), "png_format")
require(NG2Raster.decode(encoded) == normalized, "opaque_sRGB_roundtrip")
print("PASS production CoreGraphics orientation/RGBA/PNG and real C contracts; device capture not executed")
