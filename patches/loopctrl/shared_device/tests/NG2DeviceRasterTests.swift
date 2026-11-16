import Foundation
import CoreGraphics
import ImageIO

func require(_ value: Bool, _ label: String) {
    if !value { fputs("FAIL \(label)\n", stderr); exit(1) }
}

// Public synthetic JPEG fixture only. No device image, path, token or hash.
let count = 750 * 1334 * 4
let pixels = Data(repeating: 255, count: count)
let color = CGColorSpace(name: CGColorSpace.sRGB)!
let provider = CGDataProvider(data: pixels as CFData)!
let image = CGImage(width: 750, height: 1334, bitsPerComponent: 8, bitsPerPixel: 32,
    bytesPerRow: 750 * 4, space: color,
    bitmapInfo: CGBitmapInfo(rawValue: CGBitmapInfo.byteOrder32Big.rawValue |
        CGImageAlphaInfo.premultipliedLast.rawValue),
    provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent)!
let encoded = NSMutableData()
let destination = CGImageDestinationCreateWithData(encoded, "public.jpeg" as CFString, 1, nil)!
CGImageDestinationAddImage(destination, image,
    [kCGImagePropertyOrientation: 8, kCGImageDestinationLossyCompressionQuality: 0.6] as CFDictionary)
require(CGImageDestinationFinalize(destination), "real_JPEG_encoded")
let bytes = encoded as Data
let selected = "iPhone10,1".withCString { ng2_device_geometry_profile($0, 375, 667)! }
var profile = selected.pointee
var reference: Data?
for gaps in [UInt32(31), 0, 4] {
    profile.qualification_gaps = gaps
    withUnsafePointer(to: &profile) { pointer in
        switch NG2DeviceRaster.decode8(bytes, profile: pointer,
            contract: .originalPortrait750x1334EXIF8, occlusions: []) {
        case .failure:
            require(false, "identical_geometry_renders_when_input_gap_mask_\(gaps)")
        case .success(let decoded):
            if let reference { require(reference == decoded.floor.rgba, "input_gaps_do_not_change_pixels") }
            else { reference = decoded.floor.rgba }
            require(decoded.floorValidity.qualification_gaps == gaps &&
                decoded.floorValidity.input_authorized == 0, "renderer_does_not_grant_input")
        }
    }
}
profile.panel_width = 414
withUnsafePointer(to: &profile) { pointer in
    if case .success = NG2DeviceRaster.decode8(bytes, profile: pointer,
        contract: .originalPortrait750x1334EXIF8, occlusions: []) {
        require(false, "mixed_geometry_rejected")
    }
}
print("PASS actual Swift8 metadata/sampling wrapper and input-gap separation")
