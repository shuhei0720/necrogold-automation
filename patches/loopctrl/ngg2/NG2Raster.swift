import Foundation
import CoreGraphics
import ImageIO

enum NG2Raster {
    static let width = 896
    static let height = 414
    static let stride = width * 4

    /// ImageIO may defer JPEG decompression until the opaque draw. The source
    /// stage therefore measures source/image creation, not JPEG decoding alone.
    struct Trace {
        let sourceWidth: Int
        let sourceHeight: Int
        let orientation: Int
        let sourceNs: UInt64
        let drawNs: UInt64
        let orientNs: UInt64
        let scaleNs: UInt64
        let copyPixels: UInt64
    }

    struct ProfiledResult {
        let rgba: Data
        let trace: Trace
    }

    enum FailureStage: String {
        case interval, reply, source, metadata, normalize, analysis
    }

    enum FailureCode: String {
        case invalidInterval = "invalid_interval"
        case apiUnavailable = "api_unavailable"
        case sessionUnavailable = "session_unavailable"
        case displayUnprepared = "display_unprepared"
        case requestUnavailable = "request_unavailable"
        case captureFailed = "capture_failed"
        case bytesInvalid = "bytes_invalid"
        case replyException = "reply_exception"
        case requestException = "request_exception"
        case missingData = "missing_data"
        case other
        case encodedEmpty = "encoded_empty"
        case encodedLimit = "encoded_limit"
        case sourceOpen = "source_open"
        case imageCount = "image_count"
        case imageCreate = "image_create"
        case orientation
        case sourceGeometry = "source_geometry"
        case aspect
        case renderFailed = "render_failed"
        case orientationCopy = "orientation_copy"
        case invalidRGBA = "invalid_rgba"
    }

    struct Failure {
        let stage: FailureStage
        let code: FailureCode
        let encodedBytes: Int?
        let sourceWidth: Int?
        let sourceHeight: Int?
        let orientation: Int?

        init(stage: FailureStage, code: FailureCode, encodedBytes: Int? = nil,
             sourceWidth: Int? = nil, sourceHeight: Int? = nil, orientation: Int? = nil) {
            self.stage = stage
            self.code = code
            self.encodedBytes = encodedBytes
            self.sourceWidth = sourceWidth
            self.sourceHeight = sourceHeight
            self.orientation = orientation
        }
    }

    enum DecodeResult {
        case success(ProfiledResult)
        case failure(Failure)
    }

    // Executable baseline for the separate typed-failure contract. The Mac
    // assertion must observe encoded_empty before this stub is implemented.
    static func decodeDetailed(_ encoded: Data) -> DecodeResult {
        return .failure(Failure(stage: .source, code: .sourceOpen, encodedBytes: encoded.count))
    }

    /// EXIF orientation is applied before sizing. The bitmap is opaque sRGB
    /// RGBA8 with explicit byte order; no input-coordinate transform is inferred.
    static func normalize(_ image: CGImage, orientation: Int = 1,
                          outputWidth: Int = width, outputHeight: Int = height) -> Data? {
        return normalizeProfiled(image, orientation: orientation,
            outputWidth: outputWidth, outputHeight: outputHeight)?.rgba
    }

    static func normalizeProfiled(_ image: CGImage, orientation: Int = 1,
                                 outputWidth: Int = width, outputHeight: Int = height) -> ProfiledResult? {
        return normalizeProfiled(image, orientation: orientation, outputWidth: outputWidth,
            outputHeight: outputHeight, sourceNs: 0)
    }

    private static func normalizeProfiled(_ image: CGImage, orientation: Int,
                                         outputWidth: Int, outputHeight: Int,
                                         sourceNs: UInt64) -> ProfiledResult? {
        guard (1...8).contains(orientation), image.width > 0, image.height > 0,
              image.width <= 4096, image.height <= 4096,
              image.width * image.height <= 8_000_000,
              outputWidth > 0, outputHeight > 0,
              outputWidth <= 4096, outputHeight <= 4096,
              outputWidth * outputHeight <= 8_000_000,
              let space = CGColorSpace(name: CGColorSpace.sRGB) else { return nil }
        let swap = orientation >= 5
        let orientedWidth = swap ? image.height : image.width
        let orientedHeight = swap ? image.width : image.height
        guard orientedWidth * outputHeight == orientedHeight * outputWidth else { return nil }
        let drawStart = DispatchTime.now().uptimeNanoseconds
        var original = Data(count: image.width * image.height * 4)
        let decoded = original.withUnsafeMutableBytes { bytes -> Bool in
            guard let context = CGContext(data: bytes.baseAddress, width: image.width,
                height: image.height, bitsPerComponent: 8, bytesPerRow: image.width * 4,
                space: space, bitmapInfo: CGBitmapInfo.byteOrder32Big.rawValue |
                    CGImageAlphaInfo.premultipliedLast.rawValue) else { return false }
            context.setFillColor(CGColor(red: 0, green: 0, blue: 0, alpha: 1))
            context.fill(CGRect(x: 0, y: 0, width: image.width, height: image.height))
            context.setBlendMode(.normal)
            context.draw(image, in: CGRect(x: 0, y: 0, width: image.width, height: image.height))
            return true
        }
        guard decoded else { return nil }
        let drawEnd = DispatchTime.now().uptimeNanoseconds
        // Orient source pixels before CoreGraphics resampling. Explicit maps
        // make all eight EXIF cases testable with asymmetric pixel sentinels.
        var copyPixels: UInt64 = 0
        // The black fill and source-over draw already made original opaque.
        // Orientation 1 is the identity, so Data can share its storage until a
        // mutation; the remaining path only reads it while resampling.
        var oriented = original
        if orientation != 1 {
            oriented = Data(count: orientedWidth * orientedHeight * 4)
            original.withUnsafeBytes { source in
                oriented.withUnsafeMutableBytes { destination in
                    let src = source.bindMemory(to: UInt8.self)
                    let dst = destination.bindMemory(to: UInt8.self)
                    for y in 0..<orientedHeight {
                        for x in 0..<orientedWidth {
                            let p: (Int, Int)
                            switch orientation {
                            case 2: p = (image.width-1-x, y)
                            case 3: p = (image.width-1-x, image.height-1-y)
                            case 4: p = (x, image.height-1-y)
                            case 5: p = (y, x)
                            case 6: p = (y, image.height-1-x)
                            case 7: p = (image.width-1-y, image.height-1-x)
                            case 8: p = (image.width-1-y, x)
                            default: p = (x, y)
                            }
                            let a = (p.1 * image.width + p.0) * 4
                            let b = (y * orientedWidth + x) * 4
                            dst[b] = src[a]; dst[b+1] = src[a+1]; dst[b+2] = src[a+2]; dst[b+3] = 255
                        }
                        copyPixels += UInt64(orientedWidth)
                    }
                }
            }
        }
        let orientEnd = DispatchTime.now().uptimeNanoseconds
        func result(_ rgba: Data, scaleNs: UInt64) -> ProfiledResult {
            return ProfiledResult(rgba: rgba, trace: Trace(sourceWidth: image.width,
                sourceHeight: image.height, orientation: orientation, sourceNs: sourceNs,
                drawNs: drawEnd - drawStart, orientNs: orientEnd - drawEnd,
                scaleNs: scaleNs, copyPixels: copyPixels))
        }
        if orientedWidth == outputWidth && orientedHeight == outputHeight {
            return result(oriented, scaleNs: 0)
        }
        guard let provider = CGDataProvider(data: oriented as CFData),
              let orientedImage = CGImage(width: orientedWidth, height: orientedHeight,
                bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: orientedWidth * 4,
                space: space, bitmapInfo: CGBitmapInfo(rawValue:
                    CGBitmapInfo.byteOrder32Big.rawValue | CGImageAlphaInfo.premultipliedLast.rawValue),
                provider: provider, decode: nil, shouldInterpolate: true, intent: .defaultIntent) else { return nil }
        var output = Data(count: outputWidth * outputHeight * 4)
        let scaled = output.withUnsafeMutableBytes { bytes -> Bool in
            guard let context = CGContext(data: bytes.baseAddress, width: outputWidth,
                height: outputHeight, bitsPerComponent: 8, bytesPerRow: outputWidth * 4,
                space: space, bitmapInfo: CGBitmapInfo.byteOrder32Big.rawValue |
                    CGImageAlphaInfo.premultipliedLast.rawValue) else { return false }
            context.interpolationQuality = .high
            context.draw(orientedImage, in: CGRect(x: 0, y: 0, width: outputWidth, height: outputHeight))
            return true
        }
        return scaled ? result(output, scaleNs: DispatchTime.now().uptimeNanoseconds - orientEnd) : nil
    }

    static func decode(_ encoded: Data) -> Data? {
        return decodeProfiled(encoded)?.rgba
    }

    static func decodeProfiled(_ encoded: Data) -> ProfiledResult? {
        let sourceStart = DispatchTime.now().uptimeNanoseconds
        guard !encoded.isEmpty, encoded.count <= 8 * 1024 * 1024,
              let source = CGImageSourceCreateWithData(encoded as CFData, nil),
              CGImageSourceGetCount(source) == 1,
              let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else { return nil }
        let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any]
        let orientation = (properties?[kCGImagePropertyOrientation] as? NSNumber)?.intValue ?? 1
        let sourceEnd = DispatchTime.now().uptimeNanoseconds
        return normalizeProfiled(image, orientation: orientation, outputWidth: width,
            outputHeight: height, sourceNs: sourceEnd - sourceStart)
    }

    static func png(_ rgba: Data) -> Data? {
        guard rgba.count == stride * height,
              let space = CGColorSpace(name: CGColorSpace.sRGB),
              let provider = CGDataProvider(data: rgba as CFData),
              let image = CGImage(width: width, height: height, bitsPerComponent: 8,
                bitsPerPixel: 32, bytesPerRow: stride, space: space,
                bitmapInfo: CGBitmapInfo(rawValue: CGBitmapInfo.byteOrder32Big.rawValue |
                    CGImageAlphaInfo.premultipliedLast.rawValue), provider: provider,
                decode: nil, shouldInterpolate: false, intent: .defaultIntent) else { return nil }
        let result = NSMutableData()
        guard let destination = CGImageDestinationCreateWithData(result, "public.png" as CFString, 1, nil) else { return nil }
        CGImageDestinationAddImage(destination, image, nil)
        return CGImageDestinationFinalize(destination) ? result as Data : nil
    }
}
