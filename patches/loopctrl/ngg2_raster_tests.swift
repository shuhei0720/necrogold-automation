import Foundation
import CoreGraphics
import ImageIO

func require(_ value: Bool, _ label: String) {
    if !value { print("FAIL \(label)"); exit(1) }
}
func failure(_ result: NG2Raster.DecodeResult, stage: NG2Raster.FailureStage,
             code: NG2Raster.FailureCode, label: String) -> NG2Raster.Failure {
    switch result {
    case .failure(let value):
        require(value.stage == stage && value.code == code, label)
        return value
    case .success:
        require(false, label)
        fatalError()
    }
}
func detailedInputFailureContracts() {
    let empty = failure(NG2Raster.decodeDetailed(Data()), stage: .source, code: .encodedEmpty,
        label: "detailed_empty_failure_stage_and_code")
    require(empty.encodedBytes == 0 && empty.sourceWidth == nil && empty.sourceHeight == nil &&
        empty.orientation == nil, "detailed_empty_failure_keeps_unobtained_metadata_null")
    let over = failure(NG2Raster.decodeDetailed(Data(count: 8 * 1024 * 1024 + 1)),
        stage: .source, code: .encodedLimit, label: "detailed_encoded_limit_failure")
    require(over.encodedBytes == 8 * 1024 * 1024 + 1, "detailed_encoded_limit_records_actual_size")
    let invalid = failure(NG2Raster.decodeDetailed(Data([1, 2, 3])), stage: .source, code: .sourceOpen,
        label: "detailed_invalid_bytes_fail_source_creation")
    require(invalid.encodedBytes == 3 && invalid.sourceWidth == nil && invalid.sourceHeight == nil &&
        invalid.orientation == nil, "detailed_source_failure_keeps_unobtained_metadata_null")
}
if CommandLine.arguments.contains("--decode-failure-contract") {
    detailedInputFailureContracts()
    print("PASS detailed encoded-input failure contracts")
    exit(0)
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
// This assertion is intentionally first: the executable TEST045 pixel body
// reports six copied pixels, establishing behavior Red before the COW change.
let identityTrace = NG2Raster.normalizeProfiled(original, outputWidth: 3, outputHeight: 2)!
require(identityTrace.trace.copyPixels == 0,
    "orientation_1_identity_avoids_pixel_copy actual=\(identityTrace.trace.copyPixels) expected=0")
// Raster-only host shim counts entry into the real compiled C helper. Keep
// this before the full matrix so the old pixel-equivalent Swift loop yields
// the intended executable Red, without a host wall-clock performance gate.
ng2_raster_spy_reset()
require(NG2Raster.normalizeProfiled(original, orientation: 8, outputWidth: 2, outputHeight: 3) != nil,
    "orientation_8_native_path_created")
let nativeOrientationCalls = ng2_raster_spy_calls()
require(nativeOrientationCalls == 1,
    "orientation_8_uses_native_C actual=\(nativeOrientationCalls) expected=1")
detailedInputFailureContracts()
for invalidOrientation in [0, 9, Int(Int32.min), Int(Int32.max)] {
    let rejected = failure(NG2Raster.normalizeDetailed(original, orientation: invalidOrientation,
        outputWidth: 3, outputHeight: 2), stage: .metadata, code: .orientation,
        label: "detailed_invalid_orientation_rejected_\(invalidOrientation)")
    require(rejected.sourceWidth == 3 && rejected.sourceHeight == 2 &&
        rejected.orientation == invalidOrientation && rejected.encodedBytes == nil,
        "detailed_invalid_orientation_preserves_acquired_value_\(invalidOrientation)")
}
let unboundedOrientation = failure(NG2Raster.normalizeDetailed(original, orientation: Int(Int32.max) + 1,
    outputWidth: 3, outputHeight: 2), stage: .metadata, code: .orientation,
    label: "detailed_out_of_diagnostic_range_orientation_rejected")
require(unboundedOrientation.orientation == nil,
    "detailed_out_of_diagnostic_range_metadata_is_null")
for (outputWidth, outputHeight) in [(0, 0), (-1, 2), (4097, 1), (4096, 2048), (Int.max, 1)] {
    let rejected = failure(NG2Raster.normalizeDetailed(original, outputWidth: outputWidth,
        outputHeight: outputHeight), stage: .metadata, code: .sourceGeometry,
        label: "detailed_invalid_output_geometry_\(outputWidth)_\(outputHeight)")
    require(rejected.sourceWidth == 3 && rejected.sourceHeight == 2 &&
        rejected.orientation == 1, "detailed_invalid_output_keeps_source_geometry")
}
let invalidAspect = failure(NG2Raster.normalizeDetailed(original, outputWidth: 2, outputHeight: 2),
    stage: .metadata, code: .aspect, label: "detailed_aspect_failure_is_distinct")
require(invalidAspect.sourceWidth == 3 && invalidAspect.sourceHeight == 2 && invalidAspect.orientation == 1,
    "detailed_aspect_failure_keeps_source_metadata")
#if NG2_RASTER_HOST_TEST
func forcedRenderFailure(_ source: CGImage) {
    NG2Raster.HostFaults.normalizeRender = true
    defer { NG2Raster.HostFaults.normalizeRender = false }
    let rejected = failure(NG2Raster.normalizeDetailed(source, orientation: 8, outputWidth: 2, outputHeight: 3),
        stage: .normalize, code: .renderFailed, label: "detailed_render_factory_failure_is_distinct")
    require(rejected.sourceWidth == 3 && rejected.sourceHeight == 2 &&
        rejected.orientation == 8 && rejected.encodedBytes == nil,
        "detailed_render_failure_keeps_acquired_metadata")
    require(NG2Raster.normalizeProfiled(source, orientation: 8, outputWidth: 2, outputHeight: 3) == nil,
        "legacy_profiled_wrapper_refuses_render_failure")
}
forcedRenderFailure(original)
#endif
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
let invalidSource = failure(NG2Raster.normalizeDetailed(image(overLimit, 4097, 1),
    outputWidth: 4097, outputHeight: 1), stage: .metadata, code: .sourceGeometry,
    label: "detailed_oversize_source_geometry_rejected")
require(invalidSource.sourceWidth == 4097 && invalidSource.sourceHeight == 1,
    "detailed_failure_keeps_invalid_source_size_beyond_success_limit")
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
switch NG2Raster.decodeDetailed(encoded) {
case .success(let decoded):
    require(decoded.rgba == normalized && decoded.trace.sourceWidth == 896 &&
        decoded.trace.sourceHeight == 414, "detailed_success_preserves_legacy_decode_RGBA")
case .failure:
    require(false, "detailed_success_preserves_legacy_decode_RGBA")
}

func encodedImages(_ source: CGImage, type: CFString, count: Int = 1) -> Data {
    let data = NSMutableData()
    let destination = CGImageDestinationCreateWithData(data, type, count, nil)!
    for _ in 0..<count { CGImageDestinationAddImage(destination, source, nil) }
    require(CGImageDestinationFinalize(destination), "detailed_fixture_encoded")
    return data as Data
}
let multipleImages = encodedImages(original, type: "public.tiff" as CFString, count: 2)
let multipleSource = CGImageSourceCreateWithData(multipleImages as CFData, nil)!
require(CGImageSourceGetCount(multipleSource) == 2, "detailed_multiple_image_fixture_has_two_images")
let rejectedCount = failure(NG2Raster.decodeDetailed(multipleImages), stage: .source, code: .imageCount,
    label: "detailed_multiple_images_rejected_before_decode")
require(rejectedCount.encodedBytes == multipleImages.count && rejectedCount.sourceWidth == nil &&
    rejectedCount.sourceHeight == nil && rejectedCount.orientation == nil,
    "detailed_image_count_failure_has_unobtained_metadata")
let smallPNG = encodedImages(original, type: "public.png" as CFString)
let smallSource = CGImageSourceCreateWithData(smallPNG as CFData, nil)!
let smallProperties = CGImageSourceCopyPropertiesAtIndex(smallSource, 0, nil) as! [CFString: Any]
let smallOrientation = (smallProperties[kCGImagePropertyOrientation] as? NSNumber)?.intValue
let rejectedEncodedAspect = failure(NG2Raster.decodeDetailed(smallPNG), stage: .metadata, code: .aspect,
    label: "detailed_encoded_aspect_failure_is_distinct")
require(rejectedEncodedAspect.encodedBytes == smallPNG.count && rejectedEncodedAspect.sourceWidth == 3 &&
    rejectedEncodedAspect.sourceHeight == 2 && rejectedEncodedAspect.orientation == smallOrientation,
    "detailed_encoded_aspect_uses_acquired_orientation_without_inventing_default")

enum AlphaFixture: CaseIterable {
    case opaque, transparent, semialpha
}

func patternedImage(_ width: Int, _ height: Int, padding: Int = 0,
                    alpha: AlphaFixture = .opaque,
                    space: CGColorSpace = CGColorSpace(name: CGColorSpace.sRGB)!) -> CGImage {
    let rowBytes = width * 4 + padding
    var bytes = Data(repeating: 237, count: rowBytes * height)
    bytes.withUnsafeMutableBytes { raw in
        let data = raw.bindMemory(to: UInt8.self)
        for y in 0..<height {
            for x in 0..<width {
                let a: Int
                switch alpha {
                case .opaque: a = 255
                case .transparent: a = 0
                case .semialpha: a = [1, 64, 128, 192, 254][(x + y * 3) % 5]
                }
                let rgb = [(x * 37 + y * 11 + 13) % 256,
                           (x * 7 + y * 43 + 91) % 256,
                           (x * 29 + y * 19 + 173) % 256]
                let p = y * rowBytes + x * 4
                for channel in 0..<3 { data[p + channel] = UInt8((rgb[channel] * a + 127) / 255) }
                data[p + 3] = UInt8(a)
            }
        }
    }
    return CGImage(width: width, height: height, bitsPerComponent: 8, bitsPerPixel: 32,
        bytesPerRow: rowBytes, space: space,
        bitmapInfo: CGBitmapInfo(rawValue: CGBitmapInfo.byteOrder32Big.rawValue |
            CGImageAlphaInfo.premultipliedLast.rawValue),
        provider: CGDataProvider(data: bytes as CFData)!, decode: nil,
        shouldInterpolate: false, intent: .defaultIntent)!
}

func compareReference(_ source: CGImage, orientation: Int, outputWidth: Int,
                      outputHeight: Int, label: String) {
    guard let actual = NG2Raster.normalizeProfiled(source, orientation: orientation,
              outputWidth: outputWidth, outputHeight: outputHeight),
          let reference = NG2RasterReference.normalize(source, orientation: orientation,
              outputWidth: outputWidth, outputHeight: outputHeight) else {
        require(false, "\(label)_created"); return
    }
    require(actual.rgba == reference, "\(label)_all_RGBA_bytes_match_frozen_TEST045")
    let trace = actual.trace
    require(trace.sourceWidth == source.width && trace.sourceHeight == source.height &&
        trace.orientation == orientation, "\(label)_trace_source_geometry")
    require(trace.sourceNs == 0, "\(label)_direct_normalize_has_no_encoded_source_stage")
    require(trace.copyPixels == (orientation == 1 ? 0 : UInt64(source.width * source.height)),
        "\(label)_trace_counts_actual_oriented_copy_pixels")
    require(stride(from: 3, to: actual.rgba.count, by: 4).allSatisfy { actual.rgba[$0] == 255 },
        "\(label)_all_alpha_opaque")
    let orientedWidth = orientation >= 5 ? source.height : source.width
    let orientedHeight = orientation >= 5 ? source.width : source.height
    if orientedWidth == outputWidth && orientedHeight == outputHeight {
        require(trace.scaleNs == 0, "\(label)_no_resize_stage")
    }
}

// Cross every orientation/scale/stride/alpha combination with asymmetric,
// nonconstant pixels. Small custom output sizes exercise the same production
// function; a second matrix below checks its fixed 896x414 output at all scales.
var matrixCases = 0
for orientation in 1...8 {
    for scale in 1...3 {
        for padding in [0, 12] {
            for alpha in AlphaFixture.allCases {
                let sourceWidth = (orientation >= 5 ? 9 : 17) * scale
                let sourceHeight = (orientation >= 5 ? 17 : 9) * scale
                let source = patternedImage(sourceWidth, sourceHeight, padding: padding, alpha: alpha)
                compareReference(source, orientation: orientation, outputWidth: 17, outputHeight: 9,
                    label: "matrix_o\(orientation)_s\(scale)_padding\(padding)_alpha\(alpha)")
                matrixCases += 1
            }
        }
    }
}
require(matrixCases == 144, "complete_orientation_scale_stride_alpha_matrix")
for scale in 1...3 {
    let landscape = patternedImage(896 * scale, 414 * scale)
    let portrait = patternedImage(414 * scale, 896 * scale)
    for orientation in 1...8 {
        compareReference(orientation >= 5 ? portrait : landscape, orientation: orientation,
            outputWidth: 896, outputHeight: 414,
            label: "production_nonconstant_o\(orientation)_s\(scale)")
    }
}

let p3 = CGColorSpace(name: CGColorSpace.displayP3)!
let p3Source = patternedImage(51, 27, padding: 16, alpha: .semialpha, space: p3)
let sameSamplesSRGB = patternedImage(51, 27, padding: 16, alpha: .semialpha)
compareReference(p3Source, orientation: 1, outputWidth: 17, outputHeight: 9,
    label: "display_P3_color_conversion")
require(NG2Raster.normalize(p3Source, outputWidth: 17, outputHeight: 9) !=
        NG2Raster.normalize(sameSamplesSRGB, outputWidth: 17, outputHeight: 9),
    "source_color_space_affects_sRGB_conversion")

let graySpace = CGColorSpaceCreateDeviceGray()
let grayValues: [UInt8] = [0, 255, 64, 192, 32, 224, 96, 160, 17, 239, 81, 177]
let grayImage = CGImage(width: 4, height: 3, bitsPerComponent: 8, bitsPerPixel: 8,
    bytesPerRow: 4, space: graySpace,
    bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.none.rawValue),
    provider: CGDataProvider(data: Data(grayValues) as CFData)!, decode: nil,
    shouldInterpolate: false, intent: .defaultIntent)!
compareReference(grayImage, orientation: 1, outputWidth: 4, outputHeight: 3, label: "gray_to_sRGB")
let grayRGBA = NG2Raster.normalize(grayImage, outputWidth: 4, outputHeight: 3)!
require(grayRGBA.prefix(8) == Data([0, 0, 0, 255, 255, 255, 255, 255]),
    "gray_black_white_independent_expected_bytes")
var grayChannelsEqual = true
for offset in stride(from: 0, to: grayRGBA.count, by: 4) {
    let red: UInt8 = grayRGBA[offset]
    let green: UInt8 = grayRGBA[offset + 1]
    let blue: UInt8 = grayRGBA[offset + 2]
    if red != green || green != blue { grayChannelsEqual = false }
}
require(grayChannelsEqual, "gray_has_equal_RGB_channels")

func jpeg(_ source: CGImage, orientation: Int?) -> Data {
    let encoded = NSMutableData()
    let destination = CGImageDestinationCreateWithData(encoded, "public.jpeg" as CFString, 1, nil)!
    var properties: [CFString: Any] = [kCGImageDestinationLossyCompressionQuality: 0.93]
    if let orientation { properties[kCGImagePropertyOrientation] = orientation }
    CGImageDestinationAddImage(destination, source, properties as CFDictionary)
    require(CGImageDestinationFinalize(destination), "ImageIO_JPEG_encoded")
    return encoded as Data
}

func compareJPEG(_ bytes: Data, expectedWidth: Int, expectedHeight: Int,
                 orientation: Int, label: String) {
    require(bytes.starts(with: [255, 216]), "\(label)_actual_JPEG_stream")
    let source = CGImageSourceCreateWithData(bytes as CFData, nil)!
    let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as! [CFString: Any]
    let exif = (properties[kCGImagePropertyOrientation] as? NSNumber)?.intValue ?? 1
    require(exif == orientation, "\(label)_EXIF_roundtrip")
    let decodedImage = CGImageSourceCreateImageAtIndex(source, 0, nil)!
    require(decodedImage.width == expectedWidth && decodedImage.height == expectedHeight,
        "\(label)_encoded_source_geometry")
    guard let actual = NG2Raster.decodeProfiled(bytes), let reference = NG2RasterReference.decode(bytes) else {
        require(false, "\(label)_decoded"); return
    }
    require(actual.rgba == reference, "\(label)_all_RGBA_bytes_match_frozen_TEST045")
    require(NG2Raster.decode(bytes) == actual.rgba, "\(label)_legacy_decode_wrapper")
    require(actual.trace.sourceWidth == expectedWidth && actual.trace.sourceHeight == expectedHeight &&
        actual.trace.orientation == orientation, "\(label)_profiled_source_geometry")
    require(actual.trace.copyPixels == (orientation == 1 ? 0 : UInt64(expectedWidth * expectedHeight)),
        "\(label)_actual_copy_pixels")
}

let jpegLandscape = patternedImage(896, 414)
let jpegPortrait = patternedImage(414, 896)
#if NG2_RASTER_HOST_TEST
func forcedImageCreateFailure(_ bytes: Data, width: Int, height: Int, orientation: Int?) {
    NG2Raster.HostFaults.imageCreate = true
    defer { NG2Raster.HostFaults.imageCreate = false }
    let rejected = failure(NG2Raster.decodeDetailed(bytes), stage: .source, code: .imageCreate,
        label: "detailed_image_create_failure_is_distinct")
    require(rejected.encodedBytes == bytes.count && rejected.sourceWidth == width &&
        rejected.sourceHeight == height && rejected.orientation == orientation,
        "detailed_metadata_is_retained_before_image_create_factory")
    require(NG2Raster.decodeProfiled(bytes) == nil && NG2Raster.decode(bytes) == nil,
        "legacy_decode_wrappers_refuse_image_create_failure")
}
func forcedEncodedRenderFailure(_ bytes: Data) {
    NG2Raster.HostFaults.normalizeRender = true
    defer { NG2Raster.HostFaults.normalizeRender = false }
    let rejected = failure(NG2Raster.decodeDetailed(bytes), stage: .normalize, code: .renderFailed,
        label: "detailed_encoded_render_failure_is_distinct")
    require(rejected.encodedBytes == bytes.count && rejected.sourceWidth == 414 &&
        rejected.sourceHeight == 896 && rejected.orientation == 8,
        "detailed_encoded_render_failure_retains_acquired_geometry")
}
let knownEXIF8 = jpeg(jpegPortrait, orientation: 8)
forcedImageCreateFailure(knownEXIF8, width: 414, height: 896, orientation: 8)
forcedImageCreateFailure(smallPNG, width: 3, height: 2, orientation: smallOrientation)
forcedEncodedRenderFailure(knownEXIF8)
#endif
for orientation in 1...8 {
    let source = orientation >= 5 ? jpegPortrait : jpegLandscape
    compareJPEG(jpeg(source, orientation: orientation), expectedWidth: source.width,
        expectedHeight: source.height, orientation: orientation, label: "ImageIO_JPEG_EXIF_\(orientation)")
}
for scale in [2, 3] {
    let source = patternedImage(896 * scale, 414 * scale)
    compareJPEG(jpeg(source, orientation: 1), expectedWidth: source.width,
        expectedHeight: source.height, orientation: 1, label: "ImageIO_JPEG_scale_\(scale)")
}
compareJPEG(jpeg(jpegLandscape, orientation: nil), expectedWidth: 896, expectedHeight: 414,
    orientation: 1, label: "ImageIO_JPEG_missing_EXIF_defaults_1")
// ImageIO may sanitize or omit an invalid orientation while encoding. Check
// the stored property independently, then expect the decoder to obey that
// metadata; do not presume the requested value 9 survived serialization.
let attemptedInvalidJPEG = jpeg(jpegLandscape, orientation: 9)
let attemptedInvalidSource = CGImageSourceCreateWithData(attemptedInvalidJPEG as CFData, nil)!
let attemptedInvalidProperties = CGImageSourceCopyPropertiesAtIndex(attemptedInvalidSource, 0, nil) as! [CFString: Any]
let storedOrientation = (attemptedInvalidProperties[kCGImagePropertyOrientation] as? NSNumber)?.intValue
let effectiveOrientation = storedOrientation ?? 1
if (1...4).contains(effectiveOrientation) {
    // These orientations retain the encoded 896x414 aspect. A missing property
    // follows the production contract's default orientation 1.
    compareJPEG(attemptedInvalidJPEG, expectedWidth: 896, expectedHeight: 414,
        orientation: effectiveOrientation, label: "ImageIO_JPEG_encoder_sanitized_EXIF")
} else {
    // Other values are invalid, or rotate this source to the wrong aspect.
    require(NG2Raster.decodeProfiled(attemptedInvalidJPEG) == nil,
        "ImageIO_JPEG_stored_invalid_orientation_or_aspect_rejected")
}
require(NG2Raster.normalizeProfiled(original, orientation: 9, outputWidth: 3, outputHeight: 2) == nil,
    "profiled_invalid_orientation_rejected")
require(NG2Raster.normalizeProfiled(original, outputWidth: 2, outputHeight: 2) == nil,
    "profiled_invalid_aspect_rejected")
require(NG2Raster.decodeProfiled(Data()) == nil &&
    NG2Raster.decodeProfiled(Data(count: 8 * 1024 * 1024 + 1)) == nil,
    "profiled_encoded_size_bounds")
print("PASS production CoreGraphics orientation/RGBA/PNG and real C contracts; device capture not executed")
let storedOrientationLabel = storedOrientation == nil ? "absent" : String(storedOrientation!)
print("INFO ImageIO requested invalid EXIF 9; stored=\(storedOrientationLabel)")
